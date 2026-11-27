"""Execute every gold query of Spider-dev / BIRD-dev in the sandbox and report status counts.

Usage: python tools/corpus_exec_check.py DATA_ROOT   (DATA_ROOT = .../cc-by-sa-4.0)
"""
import collections, glob, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import sandbox as S

root = sys.argv[1]
report = {}
jobs = [("spider_dev", f"{root}/spider/spider_data/dev.json", f"{root}/spider/spider_data/database", "query"),
        ("bird_dev", f"{root}/bird_dev/dev_20240627/dev.json", None, "SQL")]
for name, f, dbdir, fld in jobs:
    c, t0 = collections.Counter(), time.time()
    for ex in json.load(open(f)):
        db = ex["db_id"]
        p = f"{dbdir}/{db}/{db}.sqlite" if dbdir else next(iter(glob.glob(f"{root}/bird_dev/**/dev_databases/{db}/{db}.sqlite", recursive=True)), None)
        if not p or not os.path.exists(p):
            c["missing_db"] += 1
            continue
        c[S.execute(p, ex[fld], timeout_s=10, max_rows=100000).status] += 1
    report[name] = {"n": sum(c.values()), **c, "seconds": round(time.time() - t0, 1)}
print(json.dumps(report, indent=2))
