"""Role-model feasibility with independent supervision (Vega-Lite examples). Usage: run_roles.py OUT_DIR
Grouped 5-fold CV by spec (no spec shared across folds); reports vs majority and positional baselines; exports a CANDIDATE role ONNX."""
import json, os, sys
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, precision_recall_fscore_support
from sklearn.model_selection import GroupKFold
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import experiment as E, features as F, onnx_export as OX, pipeline as P, vl_roles as V

out = sys.argv[1]; os.makedirs(out, exist_ok=True)
PIN = open(os.path.join(os.path.dirname(__file__), "..", "manifests", "vega_lite_pin.txt")).read().strip()
ex, stats, n_specs = V.fetch_examples(PIN, f"{out}/vl_role_examples.json")
X, y, g, pos = [], [], [], []
for k, e in enumerate(ex):
    t, c = F.extract("SELECT * FROM data", [{"name": n} for n in e["columns"]], e["rows"])
    for j, r in enumerate(e["roles"]):
        X.append(c[j]); y.append(r); g.append(k); pos.append(j)
X, y, g = np.stack(X), np.array(y), np.array(g)
def cv(make):
    pred = np.empty(len(y), dtype=object)
    for tr, te in GroupKFold(5).split(X, y, g):
        pred[te] = make(tr, te)
    return pred
rf = lambda tr, te: RandomForestClassifier(300, min_samples_leaf=3, class_weight="balanced", random_state=0, n_jobs=1).fit(X[tr], y[tr]).predict(X[te])
maj = lambda tr, te: np.array([max(set(y[tr]), key=list(y[tr]).count)] * len(te), dtype=object)
posb = lambda tr, te: np.array([V.ROLES[0] if pos[i] == 0 else V.ROLES[1] if pos[i] == 1 else V.ROLES[4] for i in te], dtype=object)
def boot(pred, reps=500):
    rng = np.random.default_rng(0); ug = np.unique(g); idx = {u: np.where(g == u)[0] for u in ug}; v = []
    for _ in range(reps):
        s = np.concatenate([idx[u] for u in rng.choice(ug, len(ug))]); v.append(f1_score(y[s], pred[s], labels=list(V.ROLES), average="macro", zero_division=0))
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
rep = {"experiment": "role_feasibility_vega_lite", "measures": "agreement with Vega-Lite authors' channel assignment on held-out specs; small, SQL-agnostic",
       "source": {"repo": "vega/vega-lite", "pinned_commit": PIN, "license": "BSD-3-Clause", "specs_total": n_specs, "extraction": stats},
       "n_specs": len(ex), "n_columns": int(len(y)), "role_counts": {r: int((y == r).sum()) for r in V.ROLES}, "systems": {},
       "meta": E.run_meta({"examples_sha256": P.sha256_file(f"{out}/vl_role_examples.json")})}
for name, fn in (("majority", maj), ("position_heuristic", posb), ("random_forest", rf)):
    pred = cv(fn)
    p, r, f, s = precision_recall_fscore_support(y, pred, labels=list(V.ROLES), zero_division=0)
    rep["systems"][name] = {"accuracy": float(np.mean(pred == y)), "macro_f1": float(f1_score(y, pred, labels=list(V.ROLES), average="macro", zero_division=0)),
                            "macro_f1_ci95_cluster_bootstrap": boot(pred), "per_role_f1": {V.ROLES[i]: float(f[i]) for i in range(5)}, "support": {V.ROLES[i]: int(s[i]) for i in range(5)}}
m = OX.fit_role_model(X, list(y), seed=0, n_estimators=100)
path = OX.export_role_model(m, f"{out}/role_model_candidate.onnx"); sess = OX.session(path)
ref, got = m.predict_proba(X.astype(np.float32)), OX.predict_roles_onnx(sess, X)
rep["onnx_vs_sklearn"] = {"n": int(len(X)), "max_abs_diff": float(np.abs(ref - got).max()), "within_1e-6": bool(np.allclose(ref, got, atol=1e-6, rtol=1e-6))}
rep["onnx_sha256"] = OX.sha256_file(path)
json.dump(rep, open(f"{out}/role_feasibility.json", "w"), indent=1)
print(json.dumps({k: rep[k] for k in ("n_specs", "n_columns", "role_counts", "onnx_vs_sklearn")}, indent=1))
for k, v in rep["systems"].items(): print(f"{k:20s} acc={v['accuracy']:.3f} macroF1={v['macro_f1']:.3f} CI={[round(x,2) for x in v['macro_f1_ci95_cluster_bootstrap']]} perRole={ {a: round(b,2) for a,b in v['per_role_f1'].items()} }")
