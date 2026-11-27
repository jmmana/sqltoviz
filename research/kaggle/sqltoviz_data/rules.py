"""Rules-only baseline and hard semantic constraints over the 10 base classes.

Both consume **only contract inputs** (table_features[32], column_features[M,28]) so they are
implementable identically in every SDK. Thresholds are *pre-registered hypotheses* fixed before any
experiment was run (see EXPERIMENTS.md) - tunable defaults, not universal rules (chart-taxonomy-v1).

Rules ignore metadata (units, goal, additivity), which does not exist in these corpora: additivity
and disjointness cannot be proven from SQL or data, so the constraints below are only *necessary*
data-side conditions. Unknown semantics fail closed to ``table``.
"""
from __future__ import annotations

import numpy as np

from . import features as F

CLASSES = tuple(F.contract()["model_io"]["base_classes"])
_C = F.contract()
T = {d["name"]: d["index"] for d in _C["sql_features"]}
T.update({d["name"]: 16 + d["index"] for d in _C["global_features"]})
COL = {d["name"]: d["index"] for d in _C["column_features"]}

DONUT_MAX_K = 5
HEATMAP_MIN_K = 6
LONG_LABEL = 20 / 50          # mean_string_length is divided by 50 in the contract
BAR_MAX_ROWS = 25
SCATTER_MIN_ROWS = 15


def _view(t, c):
    g = lambda n: float(t[T[n]])
    q = c[:, COL["is_quantitative"]] == 1
    n = c[:, COL["is_nominal"]] == 1
    return {"N_single": g("single_row"), "M": int(round(g("column_count"))), "nom": int(round(g("nominal_count"))),
            "quant": int(round(g("quantitative_count"))), "temp": int(round(g("temporal_count"))),
            "ident": int(round(g("identifier_count"))), "crossed": g("crossed_structure"), "minK": g("min_nominal_cardinality"),
            "small": g("small_rows"), "log_rows": g("log_row_count"), "q_cols": c[q], "n_cols": c[n]}


def _onehot(cls):
    v = np.zeros(len(CLASSES), dtype=np.float32)
    v[CLASSES.index(cls)] = 1.0
    return v


def rule_predict(t: np.ndarray, c: np.ndarray) -> str:
    v = _view(t, c)
    nonneg = bool(len(v["q_cols"]) and (v["q_cols"][:, COL["negative_ratio"]] == 0).all())
    n_rows = int(round(10 ** v["log_rows"] - 1))      # integer row count recovered from float32 log10(1+N)
    if v["N_single"] == 1 and v["M"] <= 3 and v["quant"] >= 1:
        return "kpi"
    if v["M"] >= 6:
        return "table"
    if v["crossed"] == 1:
        return "heatmap" if v["minK"] >= HEATMAP_MIN_K else "stacked_bar"
    if v["M"] == 2 and v["temp"] == 1 and v["quant"] == 1:
        return "area" if nonneg else "line"
    if v["quant"] >= 2 and v["nom"] == 0 and v["temp"] == 0 and n_rows >= SCATTER_MIN_ROWS:
        return "scatter"
    if v["M"] == 2 and v["nom"] == 1 and v["quant"] == 1:
        zero_all = bool(len(v["q_cols"]) and (v["q_cols"][:, COL["zero_ratio"]] == 1).all())
        if v["minK"] <= DONUT_MAX_K and nonneg and not zero_all:
            return "donut"
        if len(v["n_cols"]) and v["n_cols"][0, COL["mean_string_length"]] >= LONG_LABEL:
            return "horizontal_bar"
        return "bar" if n_rows <= BAR_MAX_ROWS else "table"
    return "table"


def rule_scores(t, c) -> np.ndarray:
    return _onehot(rule_predict(t, c))


def eligible(t: np.ndarray, c: np.ndarray) -> dict:
    """Necessary data-side conditions per base class (True = may be recommended). `table` is always eligible."""
    v = _view(t, c)
    qn = v["q_cols"]
    nonneg = bool(len(qn) and (qn[:, COL["negative_ratio"]] == 0).all())
    positive_total = bool(len(qn) and (qn[:, COL["zero_ratio"]] < 1).any())
    n_rows = int(round(10 ** v["log_rows"] - 1))
    cat_measure = v["nom"] >= 1 and v["quant"] >= 1 and n_rows >= 2
    ok = {
        "kpi": v["N_single"] == 1 and v["quant"] >= 1 and v["M"] <= 3,
        "bar": cat_measure,
        "horizontal_bar": cat_measure,
        "stacked_bar": v["nom"] >= 2 and v["quant"] >= 1 and nonneg and n_rows >= 4,
        "line": v["temp"] >= 1 and v["quant"] >= 1 and n_rows >= 3,
        "area": v["temp"] >= 1 and v["quant"] >= 1 and nonneg and n_rows >= 3,
        "donut": v["nom"] >= 1 and v["quant"] >= 1 and nonneg and positive_total and 2 <= v["minK"] <= 12,
        "scatter": v["quant"] >= 2 and n_rows >= 3,
        "heatmap": v["nom"] >= 2 and v["quant"] >= 1,
        "table": True,
    }
    return {k: bool(ok[k]) for k in CLASSES}


def constrained_choice(scores: np.ndarray, t, c) -> tuple:
    """Highest-scoring eligible class, else table. Returns (class, was_changed)."""
    el = eligible(t, c)
    order = np.argsort(-scores, kind="stable")
    for k in order:
        if el[CLASSES[k]]:
            return CLASSES[k], int(k) != int(order[0])
    return "table", True
