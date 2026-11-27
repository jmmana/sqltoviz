"""E1: train on synthetic, test on held-out synthetic schemas. Measures recovery of the generator's conventions
(NOT real-world accuracy). Usage: run_e1.py SYNTHETIC_JSONL OUT_JSON [seeds...]"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import experiment as E, splits as S

path, out = sys.argv[1], sys.argv[2]
seeds = [int(s) for s in sys.argv[3:]] or [0, 1, 2]
items = [json.loads(l) for l in open(path)]
X, cols = E.featurize(items)
idx = {it["item_id"]: k for k, it in enumerate(items)}
runs = []
for sd in seeds:
    assign = S.grouped_stratified_split(items, group=lambda x: x["db_id"], seed=sd)
    S.audit_splits(items, assign, group=lambda x: x["db_id"])
    tr = [i for i in items if assign[i["item_id"]] == "train"]; te = [i for i in items if assign[i["item_id"]] == "test"]
    tri, tei = [idx[i["item_id"]] for i in tr], [idx[i["item_id"]] for i in te]
    r = E.evaluate_all(tr, te, seed=sd, Xtr=X[tri], Xte=X[tei], cols_te=[cols[k] for k in tei])
    r["split_seed"] = sd
    runs.append(r)
summary = {s: {"macro_f1_mean": float(np.mean([r["systems"][s]["macro_f1"] for r in runs])),
               "macro_f1_sd": float(np.std([r["systems"][s]["macro_f1"] for r in runs])),
               "accuracy_mean": float(np.mean([r["systems"][s]["accuracy"] for r in runs])),
               "semantic_violation_rate_mean": float(np.mean([r["systems"][s]["semantic_violation_rate"] for r in runs]))}
           for s in E.SYSTEMS}
report = {"experiment": "E1_synthetic_to_synthetic_grouped_by_schema",
          "measures": "agreement with the synthetic generator's label convention on unseen schemas; not human preference, not real-world accuracy",
          "meta": E.run_meta({"dataset_sha256": E.sha256_items(items), "n_items": len(items), "split_seeds": seeds}),
          "summary": summary, "runs": runs}
json.dump(report, open(out, "w"), indent=1)
print(json.dumps(summary, indent=1))
