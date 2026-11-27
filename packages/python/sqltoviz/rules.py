"""Rules-only baseline and hard semantic constraints over the 10 base classes (port of research/kaggle/sqltoviz_data/rules.py).

Inputs are contract features only (table_features[32], column_features[M][28]). Thresholds are pre-registered tunable
hypotheses, not universal rules. Constraints are only *necessary* data-side conditions: additivity, hierarchy, units and goals
cannot be proven from SQL or data, and unknown semantics fail closed to ``table``.
"""
from __future__ import annotations

from ._contract import BASE_CLASSES, COLUMN_FEATURES, GLOBAL_FEATURES, SQL_FEATURES

T = {n: i for i, (n, *_r) in enumerate(SQL_FEATURES)}
T.update({n: 16 + i for i, (n, *_r) in enumerate(GLOBAL_FEATURES)})
COL = {n: i for i, (n, *_r) in enumerate(COLUMN_FEATURES)}
DONUT_MAX_K, HEATMAP_MIN_K, LONG_LABEL, BAR_MAX_ROWS, SCATTER_MIN_ROWS = 5, 6, 20 / 50, 25, 15


def _view(t, c):
    g = lambda n: float(t[T[n]])
    q = [r for r in c if r[COL["is_quantitative"]] == 1]
    n = [r for r in c if r[COL["is_nominal"]] == 1]
    return {"single": g("single_row"), "M": int(round(g("column_count"))), "nom": int(round(g("nominal_count"))),
            "quant": int(round(g("quantitative_count"))), "temp": int(round(g("temporal_count"))), "crossed": g("crossed_structure"),
            "minK": g("min_nominal_cardinality"), "log_rows": g("log_row_count"), "q_cols": q, "n_cols": n}


def _rows(v):
    return int(round(10 ** v["log_rows"] - 1))  # integer row count recovered from float32 log10(1+N)


def rule_predict(t, c) -> str:
    v = _view(t, c)
    q = v["q_cols"]
    nonneg = bool(q) and all(r[COL["negative_ratio"]] == 0 for r in q)
    n_rows = _rows(v)
    if v["single"] == 1 and v["M"] <= 3 and v["quant"] >= 1:
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
        zero_all = bool(q) and all(r[COL["zero_ratio"]] == 1 for r in q)
        if v["minK"] <= DONUT_MAX_K and nonneg and not zero_all:
            return "donut"
        if v["n_cols"] and v["n_cols"][0][COL["mean_string_length"]] >= LONG_LABEL:
            return "horizontal_bar"
        return "bar" if n_rows <= BAR_MAX_ROWS else "table"
    return "table"


def eligible(t, c) -> dict:
    v = _view(t, c)
    q = v["q_cols"]
    nonneg = bool(q) and all(r[COL["negative_ratio"]] == 0 for r in q)
    positive_total = bool(q) and any(r[COL["zero_ratio"]] < 1 for r in q)
    n_rows = _rows(v)
    cat_measure = v["nom"] >= 1 and v["quant"] >= 1 and n_rows >= 2
    ok = {
        "kpi": v["single"] == 1 and v["quant"] >= 1 and v["M"] <= 3,
        "bar": cat_measure, "horizontal_bar": cat_measure,
        "stacked_bar": v["nom"] >= 2 and v["quant"] >= 1 and nonneg and n_rows >= 4,
        "line": v["temp"] >= 1 and v["quant"] >= 1 and n_rows >= 3,
        "area": v["temp"] >= 1 and v["quant"] >= 1 and nonneg and n_rows >= 3,
        "donut": v["nom"] >= 1 and v["quant"] >= 1 and nonneg and positive_total and 2 <= v["minK"] <= 12,
        "scatter": v["quant"] >= 2 and n_rows >= 3,
        "heatmap": v["nom"] >= 2 and v["quant"] >= 1,
        "table": True,
    }
    return {k: bool(ok[k]) for k in BASE_CLASSES}


def constrained_choice(scores, t, c) -> tuple:
    """Highest-scoring eligible class (stable order on ties), else table. Returns (class, changed)."""
    el = eligible(t, c)
    order = sorted(range(len(scores)), key=lambda k: (-scores[k], k))
    for k in order:
        if el[BASE_CLASSES[k]]:
            return BASE_CLASSES[k], k != order[0]
    return "table", True
