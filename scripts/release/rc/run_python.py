"""Runs golden fixtures through the INSTALLED sqltoviz wheel (run with `python -I` from a clean venv). Usage: run_python.py GOLDEN OUT"""
import hashlib, json, pathlib, sys
import sqltoviz
from sqltoviz import Engine, FeatureError

golden = json.load(open(sys.argv[1]))
order = golden["class_order"]
eng = Engine.default()
out = {"package": "sqltoviz " + getattr(sqltoviz, "__version__", "?"), "location": str(pathlib.Path(sqltoviz.__file__).parent), "cases": {}}
mdir = pathlib.Path(sqltoviz.__file__).parent / "models"
out["models"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(mdir.glob("*.onnx"))}
for c in golden["cases"]:
    try:
        r = eng.recommend(c["sql"], c["schema"], c["rows"])
    except FeatureError:
        out["cases"][c["case_id"]] = {"rejected": True}
        continue
    out["cases"][c["case_id"]] = {
        "model_status": r["model_status"], "base_class": r["base_class"], "final_class": r["final_class"], "rule_class": r["rule_class"],
        "constraint_changed": r["constraint_changed"], "eligible": r["eligible"], "scores": [r["scores"][k] for k in order],
        "roles": [x["role"] for x in r["roles"]], "role_scores": [x["scores"] for x in r["roles"]]}
json.dump(out, open(sys.argv[2], "w"))
