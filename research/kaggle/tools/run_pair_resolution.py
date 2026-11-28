"""Can bar/horizontal_bar and line/area be separated without changing the frozen contract?
(a) post-model deterministic resolver using column features already defined in SqlVizSpec-v1.0.0 (thresholds chosen on VALIDATION, reported on TEST);
(b) contract-extension study (informative only): add three column aggregates to the chart model input.
Usage: run_pair_resolution.py SYNTH_JSONL FEATURES_NPZ OUT_JSON [seeds...]. Labels are synthetic: results measure agreement with the generator convention."""
import json, os, sys
import numpy as np
from sklearn.metrics import f1_score
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import experiment as E, pipeline as P, rules as R, splits as S

jsonl, npz, out = sys.argv[1:4]
seeds = [int(x) for x in sys.argv[4:]] or [0, 1, 2]
syn = {json.loads(l)["item_id"]: json.loads(l) for l in open(jsonl)}
fs = P.load_features(npz)
items = [syn[i] for i in fs["item_ids"]]
X, C = fs["table"], fs["columns"]
y = np.array([i["label"] for i in items])
COL = R.COL; CL = list(R.CLASSES)


def resolve(pred, table, cols, L, Rn):
    """pred: class after constraints. Pair resolver from contract column features only."""
    el = R.eligible(table, cols)
    if pred in ("bar", "horizontal_bar"):
        nom = [r for r in cols if r[COL["is_nominal"]] == 1]
        longest = max((r[COL["mean_string_length"]] for r in nom), default=0.0)
        cand = "horizontal_bar" if longest >= L else "bar"
        return cand if el[cand] else pred
    if pred in ("line", "area"):
        q = [r for r in cols if r[COL["is_quantitative"]] == 1]
        nonneg = bool(q) and all(r[COL["negative_ratio"]] == 0 for r in q)
        span = max((r[COL["normalized_range"]] for r in q), default=0.0)
        cand = "area" if (nonneg and span >= Rn) else "line"
        return cand if el[cand] else pred
    return pred


def extra_feats(table, cols):
    nom = [r for r in cols if r[COL["is_nominal"]] == 1]; q = [r for r in cols if r[COL["is_quantitative"]] == 1]
    return [max((r[COL["mean_string_length"]] for r in nom), default=0.0), float(bool(q) and all(r[COL["negative_ratio"]] == 0 for r in q)),
            max((r[COL["normalized_range"]] for r in q), default=0.0)]


def pair_f1(yt, yp, a, b):
    return {c: float(f1_score(yt, yp, labels=[c], average="macro", zero_division=0)) for c in (a, b)}


runs = []
for sd in seeds:
    asg = S.grouped_stratified_split(items, group=lambda x: x["db_id"], seed=sd, ratios=(0.6, 0.2, 0.2))
    idx = {s: [k for k, it in enumerate(items) if asg[it["item_id"]] == s] for s in ("train", "val", "test")}
    m = E.make_rf(sd).fit(X[idx["train"]], y[idx["train"]])
    def predict(split, resolver=None):
        sc = E._proba_full(m, X[idx[split]]); out = []
        for r, k in enumerate(idx[split]):
            p, _ = R.constrained_choice(sc[r], X[k], C[k])
            out.append(resolver(p, X[k], C[k]) if resolver else p)
        return np.array(out)
    labels = lambda split: [c for c in CL if c in set(y[idx[split]])]
    mf = lambda split, p: float(f1_score(y[idx[split]], p, labels=labels(split), average="macro", zero_division=0))
    grid = [(L, Rn) for L in (0.2, 0.3, 0.4, 0.5, 0.6) for Rn in (0.25, 0.5, 0.75, 1.0, 1.5)]
    val_scores = {g: mf("val", predict("val", lambda p, t, c, g=g: resolve(p, t, c, *g))) for g in grid}
    best = max(val_scores, key=val_scores.get)
    base_t, cons_t = None, predict("test")
    raw = np.array([CL[k] for k in E._proba_full(m, X[idx["test"]]).argmax(1)])
    res_t = predict("test", lambda p, t, c: resolve(p, t, c, *best))
    # (b) contract-extension study
    Xe = np.hstack([X, np.array([extra_feats(X[k], C[k]) for k in range(len(items))])])
    me = E.make_rf(sd).fit(Xe[idx["train"]], y[idx["train"]])
    ext = np.array([CL[k] for k in E._proba_full(me, Xe[idx["test"]]).argmax(1)])
    yt = y[idx["test"]]
    runs.append({"split_seed": sd, "chosen_on_validation": {"L_label_length": best[0], "R_normalized_range": best[1]},
                 "test_macro_f1": {"hybrid_raw": mf("test", raw), "hybrid_constraints": mf("test", cons_t), "hybrid_constraints_pair_resolver": mf("test", res_t), "extended_input_study": mf("test", ext)},
                 "test_pair_f1": {k: {"bar_horizontal_bar": pair_f1(yt, v, "bar", "horizontal_bar"), "line_area": pair_f1(yt, v, "line", "area")}
                                  for k, v in (("hybrid_raw", raw), ("hybrid_constraints", cons_t), ("pair_resolver", res_t), ("extended_input_study", ext))},
                 "validation_grid_macro_f1": {f"L={g[0]},R={g[1]}": v for g, v in val_scores.items()}})
agg = {k: [float(np.mean([r["test_macro_f1"][k] for r in runs])), float(np.std([r["test_macro_f1"][k] for r in runs]))] for k in runs[0]["test_macro_f1"]}
rep = {"experiment": "pair_resolution", "measures": "agreement with the synthetic generator convention on unseen schemas; NOT human preference; thresholds chosen on validation",
       "meta": E.run_meta({"seeds": seeds}), "test_macro_f1_mean_sd": agg, "runs": runs}
json.dump(rep, open(out, "w"), indent=1)
print(json.dumps(agg, indent=1))
for r in runs[:1]: print(json.dumps({k: v for k, v in r["test_pair_f1"].items()}, indent=0)[:900])
