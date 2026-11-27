"""Dedup + grouped-split report on Spider(train,dev) and BIRD(dev) using a *stand-in* stratum
(result column count / aggregate flag). NOT chart labels - those come from annotation (#24)."""
import json, os, sys, re
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import splits as S

root = sys.argv[1]; sp = f"{root}/spider/spider_data"; bd = f"{root}/bird_dev/dev_20240627"
def rows(path, sqlk, src):
    return [{"item_id": f"{src}_{i}", "db_id": e["db_id"], "sql": e[sqlk], "src": src} for i, e in enumerate(json.load(open(path)))]
tr, dv, bi = rows(f"{sp}/train_spider.json", "query", "spider_train"), rows(f"{sp}/dev.json", "query", "spider_dev"), rows(f"{bd}/dev.json", "SQL", "bird_dev")
dbs = {k: {r["db_id"] for r in v} for k, v in {"spider_train": tr, "spider_dev": dv, "bird_dev": bi}.items()}
overlap = {f"{a}&{b}": sorted(dbs[a] & dbs[b]) for a, b in [("spider_train", "spider_dev"), ("spider_train", "bird_dev"), ("spider_dev", "bird_dev")]}
print("db counts", {k: len(v) for k, v in dbs.items()})
print("db overlap", {k: (len(v), v[:8]) for k, v in overlap.items()})
allr = tr + dv + bi
for r in allr:  # group = canonical db name: same-named DBs from different corpora (e.g. formula_1) must stay together
    r["group"] = r["db_id"]
    s = r["sql"].lower()
    r["label"] = f"cols{min(len(re.findall(r',', s.split(' from ')[0])) + 1, 3)}_{'agg' if re.search(r'count|sum|avg|min|max', s) else 'raw'}"
kept, dropped, st = S.dedup(allr, group=lambda x: x["group"])
print("dedup", st)
a = S.grouped_stratified_split(kept, group=lambda x: x["group"], seed=20261127)
rep = S.audit_splits(kept, a, group=lambda x: x["group"])
print(json.dumps({k: {"n": v["n"], "groups": v["groups"]} for k, v in rep["splits"].items()}))
