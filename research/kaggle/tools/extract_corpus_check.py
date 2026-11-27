"""Run the full extractor (SQL + executed result) over Spider-dev / BIRD-dev; report rejections and type mix."""
import collections, glob, json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import features as F, sandbox as S

root = sys.argv[1]
jobs = [("spider_dev", f"{root}/spider/spider_data/dev.json", f"{root}/spider/spider_data/database", "query"),
        ("bird_dev", f"{root}/bird_dev/dev_20240627/dev.json", None, "SQL")]
rep = {}
for name, f, dbdir, fld in jobs:
    c, types, t0 = collections.Counter(), collections.Counter(), time.time()
    for ex in json.load(open(f)):
        db = ex["db_id"]
        p = f"{dbdir}/{db}/{db}.sqlite" if dbdir else next(iter(glob.glob(f"{root}/bird_dev/**/dev_databases/{db}/{db}.sqlite", recursive=True)), None)
        r = S.execute(p, ex[fld], timeout_s=10, max_rows=F.MAX_ROWS + 1)
        if r.status != "ok":
            c["not_executable"] += 1; continue
        if r.truncated or not r.rows:
            c["out_of_bounds_or_empty"] += 1; continue
        if len(r.columns) > F.MAX_COLUMNS:
            c["too_many_columns"] += 1; continue
        try:
            t, m = F.extract(ex[fld], [{"name": n} for n in r.columns], r.rows)
            assert np.isfinite(t).all() and np.isfinite(m).all()
            c["ok"] += 1
            for row in m:
                types[("temporal", "quantitative", "nominal", "identifier")[int(np.argmax(row[1:5]))]] += 1
        except F.FeatureError as e:
            c["rejected:" + str(e)[:40]] += 1
    rep[name] = {"n": sum(c.values()), **c, "column_types": dict(types), "seconds": round(time.time() - t0, 1)}
print(json.dumps(rep, indent=1))
