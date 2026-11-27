"""Build a blind annotation task pack from Spider train queries (executed in the sandbox).

Usage: python tools/make_task_pack.py DATA_ROOT OUT.jsonl N SEED
Only SQL text, column names and a 20-row preview are emitted (no labels/features).
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import annotations as A, sandbox as S

root, out, n, seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
base = f"{root}/spider/spider_data"
cands = []
for i, ex in enumerate(json.load(open(f"{base}/train_spider.json"))):
    r = S.execute(f"{base}/database/{ex['db_id']}/{ex['db_id']}.sqlite", ex["query"], timeout_s=5, max_rows=21)
    if r.status == "ok" and r.rows and len(r.columns) >= 1:
        cands.append({"item_id": f"spider_train_{i}", "db_id": ex["db_id"], "sql": ex["query"],
                      "columns": r.columns, "rows_preview": r.rows[:20], "result_truncated": r.truncated})
pack = A.build_task_pack(cands, n, seed)
with open(out, "w") as f:
    for p in pack:
        f.write(json.dumps(p, default=str) + "\n")
print(json.dumps({"candidates": len(cands), "pack": len(pack), "dbs": len({p['db_id'] for p in pack}), "seed": seed}))
