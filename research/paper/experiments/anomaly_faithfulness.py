"""RQ8: anomaly accuracy on injected anomalies + numerical faithfulness of the Python detectors.
Usage: anomaly_faithfulness.py OUT_JSON   (needs numpy, scipy; imports packages/python/sqltoviz from the repo)
Evaluates the Python SDK alpha only. Synthetic Gaussian data with known injected outliers: results describe this controlled setting."""
import json, math, os, random, sys
from decimal import Decimal, getcontext
import numpy as np
from scipy import stats
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages", "python"))
from sqltoviz import statistics as S

getcontext().prec = 80
rng = np.random.default_rng(20261127)


def trial(n, contamination, mag):
    x = rng.normal(0, 1, n)
    k = max(1, int(round(contamination * n)))
    idx = rng.choice(n, k, replace=False)
    sign = rng.choice([-1, 1], k)
    x[idx] = sign * mag + rng.normal(0, 0.1, k)
    return x, set(int(i) for i in idx)


def prf(flag, truth, n):
    tp, fp = len(flag & truth), len(flag - truth)
    return tp, fp, len(truth), n - len(truth)


def zscore_flags(x, t=3.0):
    sd = x.std(ddof=0)
    return set(int(i) for i in np.where(np.abs((x - x.mean()) / sd) > t)[0]) if sd > 0 else set()


# ---------------- A. injected anomalies (MAD detector vs classical z-score)
accuracy = []
for n in (20, 100, 1000):
    for cont in (0.02, 0.10, 0.20):
        for mag in (4, 6, 10):
            agg = {"mad": [0, 0, 0, 0], "zscore": [0, 0, 0, 0]}
            for _ in range(200):
                x, truth = trial(n, cont, mag)
                f1 = set(o["index"] for o in S.mad_outliers(x.tolist())["outliers"])
                f2 = zscore_flags(x)
                for name, f in (("mad", f1), ("zscore", f2)):
                    for j, v in enumerate(prf(f, truth, n)):
                        agg[name][j] += v
            row = {"n": n, "contamination": cont, "magnitude_sigma": mag, "trials": 200}
            for name, (tp, fp, pos, neg) in agg.items():
                row[name] = {"recall": tp / pos, "precision": tp / (tp + fp) if tp + fp else None, "false_positive_rate": fp / neg}
            accuracy.append(row)
clean = {}
for n in (20, 100, 1000):
    flagged_series = pts = 0
    for _ in range(2000):
        x = rng.normal(0, 1, n)
        o = S.mad_outliers(x.tolist())["outliers"]
        flagged_series += bool(o); pts += len(o)
    clean[str(n)] = {"series_with_any_flag": flagged_series / 2000, "point_false_positive_rate": pts / (2000 * n)}

# ---------------- B. numerical faithfulness vs independent references
def rel(a, b):
    return abs(a - b) / max(abs(b), 1e-300)

mad_err, pearson_err, shift_err, pareto_err = [], [], [], []
cases = 0
for _ in range(600):
    n = int(rng.integers(5, 200)); scale = 10.0 ** rng.integers(-8, 9); off = rng.choice([0, 1, 1e3])
    x = rng.normal(0, 1, n) * scale + off * scale
    if rng.random() < 0.3:
        x = np.round(x)
    r = S.mad_outliers(x.tolist())
    med = float(np.median(x)); mad = float(stats.median_abs_deviation(x, scale=1))
    if r["status"] == "ok":
        mad_err.append(max(rel(r["median"], med) if med else abs(r["median"]), rel(r["mad"], mad)))
        ref = {i: 0.6744897501960817 * (x[i] - med) / mad for i in range(n)}
        got = {o["index"]: o["score"] for o in r["outliers"]}
        mad_err.append(max([rel(got[i], ref[i]) for i in got] or [0.0]))
        ref_flag = {i for i, z in ref.items() if abs(z) > 3.5}
        assert ref_flag == set(got), "flag set differs from independent recomputation"
    cases += 1
    a = rng.normal(0, 1, n) * scale + off * scale
    b = 0.7 * a + rng.normal(0, 1, n) * scale
    got = S.pearson(a.tolist(), b.tolist())["r"]
    # exact reference with 80-digit decimals on the exact binary values
    A, B = [Decimal(float(v)) for v in a], [Decimal(float(v)) for v in b]
    ma, mb = sum(A) / n, sum(B) / n
    num = sum((p - ma) * (q - mb) for p, q in zip(A, B))
    den = (sum((p - ma) ** 2 for p in A) * sum((q - mb) ** 2 for q in B)).sqrt()
    exact = float(num / den)
    pearson_err.append({"impl": abs(got - exact), "numpy": abs(float(np.corrcoef(a, b)[0, 1]) - exact)})
    v = (rng.normal(5, 2, n) * scale).tolist()
    sh = S.temporal_shifts(v)
    for s_ in sh:
        i = s_["index"]
        if s_["status"] == "ok":
            shift_err.append(max(abs(s_["delta"] - (v[i] - v[i - 1])) / max(abs(v[i] - v[i - 1]), 1e-300), rel(s_["relative_change"], (v[i] - v[i - 1]) / abs(v[i - 1]))))
    w = np.abs(rng.normal(10, 5, n)) * scale
    p = S.pareto(w.tolist(), 0.8, additive=True)
    if p["status"] == "ok":
        order = np.argsort(-w, kind="stable"); cum = np.cumsum(w[order]) / w.sum()
        got_c = {it["index"]: it["cumulative"] for it in p["items"]}
        pareto_err.append(max(abs(got_c[int(order[k])] - cum[k]) for k in range(n)))
# degenerate and extreme inputs
degenerate = {
    "zero_mad_status": S.mad_outliers([1, 1, 1, 1, 9])["status"],
    "too_few_samples": S.mad_outliers([1, 2])["status"],
    "overflow_values": S.mad_outliers([1e308, -1e308, 0.0, 1.0, 2.0])["status"],
    "pearson_constant": S.pearson([1, 1, 1, 1], [1, 2, 3, 4])["status"],
    "pearson_huge_offset_r": S.pearson([1e9 + i for i in range(10)], [2 * i for i in range(10)])["r"],
    "pareto_without_additivity": S.pareto([1, 2, 3])["status"],
    "pareto_negative": S.pareto([1, -2, 3], additive=True)["status"],
    "shift_zero_baseline": S.temporal_shifts([0, 5])[0]["status"],
}
rep = {"scope": "Python SDK alpha detectors on synthetic Gaussian data; not TypeScript/.NET, not real data",
       "injected_anomaly_accuracy": accuracy, "clean_series_false_alarms": clean,
       "faithfulness": {"cases": cases, "mad_max_relative_error": max(mad_err), "pearson_max_abs_error_impl": max(e["impl"] for e in pearson_err),
                        "pearson_max_abs_error_numpy": max(e["numpy"] for e in pearson_err),
                        "temporal_shift_max_relative_error": max(shift_err), "pareto_max_abs_error": max(pareto_err),
                        "mad_flag_set_equal_to_independent_recomputation": True},
       "degenerate_behaviour": degenerate}
json.dump(rep, open(sys.argv[1], "w"), indent=1)
print(json.dumps(rep["faithfulness"], indent=1)); print(json.dumps(clean)); print(degenerate)
for r in accuracy:
    if r["n"] == 100: print(r["contamination"], r["magnitude_sigma"], "MAD", {k: round(v, 3) if v is not None else None for k, v in r["mad"].items()}, "Z", {k: round(v, 3) if v is not None else None for k, v in r["zscore"].items()})
