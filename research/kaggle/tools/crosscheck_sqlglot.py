"""Cross-check lexical SQL features against sqlglot's AST on Spider-dev + BIRD-dev gold queries.
sqlglot is an independent implementation: disagreements are reported, then inspected, not hidden."""
import json, os, sys, collections
import sqlglot
from sqlglot import exp
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import features as F

root = sys.argv[1]
qs = [e["query"] for e in json.load(open(f"{root}/spider/spider_data/dev.json"))] + \
     [e["SQL"] for e in json.load(open(f"{root}/bird_dev/dev_20240627/dev.json"))]
names = {d["name"]: d["index"] for d in F.contract()["sql_features"]}
checks = {
    "join_count": lambda a: len(list(a.find_all(exp.Join))),
    "has_group_by": lambda a: int(a.find(exp.Group) is not None),
    "has_order_by": lambda a: int(a.find(exp.Order) is not None),
    "has_limit": lambda a: int(a.find(exp.Limit) is not None),
    "has_distinct": lambda a: int(a.find(exp.Distinct) is not None or any(isinstance(c, exp.Select) and c.args.get("distinct") for c in a.find_all(exp.Select))),
    "has_having": lambda a: int(a.find(exp.Having) is not None),
    "has_window": lambda a: int(a.find(exp.Window) is not None),
    "subquery_cte_count": lambda a: len(list(a.find_all(exp.Subquery))) + len(list(a.find_all(exp.CTE))),
}
agree, total, bad, skipped = collections.Counter(), collections.Counter(), collections.defaultdict(list), 0
for q in qs:
    try:
        ast = sqlglot.parse_one(q, read="sqlite")
        f = F.sql_features(q, [])
    except Exception:
        skipped += 1
        continue
    for k, fn in checks.items():
        total[k] += 1
        mine, ref = f[names[k]], fn(ast)
        if k.startswith("has_"):
            mine, ref = int(mine > 0), int(ref > 0)
        if int(mine) == int(ref):
            agree[k] += 1
        elif len(bad[k]) < 3:
            bad[k].append((q[:140], mine, ref))
print(json.dumps({"n_queries": len(qs), "skipped": skipped,
                  "agreement": {k: round(agree[k] / total[k], 4) for k in checks}}, indent=1))
for k, v in bad.items():
    print("MISMATCH", k)
    for x in v:
        print("   ", x)
