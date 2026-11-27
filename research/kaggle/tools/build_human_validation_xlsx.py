"""Build the blind human-validation workbook for the 100 reserved pilot items.
Usage: build_human_validation_xlsx.py DATA_ROOT(cc-by-sa-4.0) OUT_DIR"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import features as F, human_validation as H, sandbox as S

root, out = sys.argv[1:3]
here = os.path.join(os.path.dirname(__file__), "..")
ids = json.load(open(f"{here}/annotations/human_validation_reserve_ids.json"))
base = f"{root}/spider/spider_data"
train = json.load(open(f"{base}/train_spider.json"))
cases = []
for iid in ids:
    ex = train[int(iid.rsplit("_", 1)[1])]
    r = S.execute(f"{base}/database/{ex['db_id']}/{ex['db_id']}.sqlite", ex["query"], timeout_s=10, max_rows=F.MAX_ROWS + 1)
    assert r.status == "ok" and r.rows, (iid, r.status)
    cases.append({"item_id": iid, "db_id": ex["db_id"], "sql": ex["query"], "columns": r.columns, "rows": r.rows})
os.makedirs(out, exist_ok=True)
key = H.build_workbook(cases, f"{out}/human_validation_100_cases.xlsx", f"{out}/human_validation_key.csv")
print(json.dumps({"cases": len(key), "workbook": f"{out}/human_validation_100_cases.xlsx"}))
