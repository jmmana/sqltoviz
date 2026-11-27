"""Re-execute the blind pack in the sandbox to obtain FULL result sets (for feature extraction).
Usage: build_pilot_items.py DATA_ROOT PACK_JSONL OUT_JSONL   (output stays in the cc-by-sa-4.0 namespace; never committed)"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import features as F, sandbox as S
root, pack, out = sys.argv[1:4]
base = f"{root}/spider/spider_data/database"
kept = skipped = 0
with open(out, "w") as f:
    for l in open(pack):
        it = json.loads(l)
        r = S.execute(f"{base}/{it['db_id']}/{it['db_id']}.sqlite", it["sql"], timeout_s=10, max_rows=F.MAX_ROWS + 1)
        if r.status != "ok" or r.truncated or not r.rows:
            skipped += 1; continue
        f.write(json.dumps({"item_id": it["item_id"], "db_id": it["db_id"], "sql": it["sql"], "columns": r.columns, "rows": r.rows}, default=str) + "\n")
        kept += 1
print(json.dumps({"kept": kept, "skipped": skipped}))
