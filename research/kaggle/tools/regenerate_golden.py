"""Rebuild parity/golden_v1.json (additive fields: classification, eligibility, roles) from its own inputs and the candidate models.
Usage: regenerate_golden.py [REPO_ROOT]"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import golden as G, onnx_export as OX

root = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "..")
old = json.load(open(f"{root}/parity/golden_v1.json"))
cases = [{k: c[k] for k in ("case_id", "kind", "sql", "schema", "rows", "expect")} | ({"generator_label": c["generator_label"]} if "generator_label" in c else {}) for c in old["cases"]]
have = {c["case_id"] for c in cases}
cases += [c for c in G.extension_cases() if c["case_id"] not in have]   # appended after the original 288; existing cases untouched
sess, rsess = OX.session(f"{root}/model/candidate/chart_model_candidate.onnx"), OX.session(f"{root}/model/candidate/role_model_candidate.onnx")
g = G.build_golden(cases, sess, rsess)
rep = G.verify_golden(json.loads(json.dumps(g)), sess, rsess)
assert not rep["failures"], rep["failures"]
json.dump(g, open(f"{root}/parity/golden_v1.json", "w"))
print(json.dumps({k: rep[k] for k in ("n_cases", "accepted_ok", "rejected_ok", "max_abs_diff")}))
