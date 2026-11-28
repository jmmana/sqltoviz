"""SqlVizSpec-Outputs-v1.0.0 reference implementation: specialise a base chart class into one of 21 concrete outputs.

Additive extension (spec/sqlvizspec-v1-outputs.json, spec/OUTPUTS_V1.md). Nothing here changes the frozen base contract, the ONNX models
or the base eligibility rules. Preconditions are deterministic and run in the order the spec lists them; the first failing one is the
rejection reason. Metadata that is absent or malformed fails closed for every output that needs it. Pure standard library.
"""
from __future__ import annotations

import math
from collections import Counter

from ._outputs import ALIASES, DEFINITIONS, OUTPUTS, SPECIALIZATION, THRESHOLDS
from ._contract import BASE_CLASSES
from .features import _quantile7, _sum, is_missing, parse_temporal, resolve_type

MAX_CAT = THRESHOLDS["max_categories_bar"]


def normalize_output(name: str) -> str:
    """Map legacy aliases (``kpi_card``) to the canonical output name."""
    return ALIASES.get(name, name)


def resolve_columns(columns: list, rows: list) -> list:
    """Return [{'name', 'type'}] with types resolved by the base contract rules (explicit ``type`` honoured, else inferred)."""
    cols = [{"name": c} if isinstance(c, str) else c for c in columns]
    return [{"name": c["name"], "type": resolve_type(c["name"], [r[j] for r in rows], c.get("type"))} for j, c in enumerate(cols)]


def _isnum(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


class _Ctx:
    def __init__(self, columns, rows, meta, roles, el):
        self.cols = columns
        self.rows = rows
        self.N = len(rows)
        self.meta = meta if isinstance(meta, dict) else {}
        self.roles = roles if isinstance(roles, dict) else {}
        self.el = el
        self.idx = {c["name"]: j for j, c in enumerate(columns)}
        self.reset()

    def reset(self):
        self.enc, self.params, self.used, self.dims, self.sample, self.group, self.output, self.carriers = {}, {}, [], [], None, None, None, ()

    def vals(self, name):
        j = self.idx[name]
        return [r[j] for r in self.rows]

    def of_type(self, t, role=None, exclude=()):
        c = [x["name"] for x in self.cols if x["type"] == t and x["name"] not in exclude and self.roles.get(x["name"]) != "ignore_tooltip"]
        if role:
            pref = [n for n in c if self.roles.get(n) == role]
            c = pref + [n for n in c if n not in pref]
        return c

    def colmeta(self, name):
        m = self.meta.get("columns")
        m = m.get(name) if isinstance(m, dict) else None
        return m if isinstance(m, dict) else {}

    def flag(self, key):
        return self.meta.get(key) is True

    def unique_count(self, names):
        return len({tuple(self._k(n, r) for n, r in zip(names, row)) for row in zip(*[self.vals(n) for n in names])})

    def _k(self, n, v):
        return parse_temporal(v) if self.cols[self.idx[n]]["type"] == "temporal" else (float(v) if _isnum(v) else v)


# ------------------------------------------------------------------ shape checks (they also bind the encoding columns)
def _shape_cat(c):
    n, q = c.of_type("nominal", "x_axis"), c.of_type("quantitative", "y_axis")
    if not n or not q:
        return False
    c.enc = {"category": n[0], "value": q[0]}
    c.dims, c.used = [n[0]], [n[0], q[0]]
    return True


def _shape_two(c):
    n, q = c.of_type("nominal", "x_axis"), c.of_type("quantitative", "y_axis")
    if len(n) < 2 or not q:
        return False
    cat = n[0]
    ser = c.of_type("nominal", "color_series", exclude=(cat,))[0]
    if c.output == "heatmap":
        c.enc = {"row": cat, "column": ser, "value": q[0]}
    else:
        c.enc = {"category": cat, "series": ser, "value": q[0]}
    c.dims, c.used = [cat, ser], [cat, ser, q[0]]
    return True


def _shape_time(c, want_q=1):
    t, q = c.of_type("temporal", "x_axis"), c.of_type("quantitative", "y_axis")
    if not t or len(q) < want_q:
        return False
    if want_q == 2:
        return _shape_dual(c, t[0])
    c.enc = {"x": t[0], "y": q[0]}
    c.dims, c.used = [t[0]], [t[0], q[0]]
    return True


def _shape_dual(c, t):
    c.enc, c.dims = {"x": t}, [t]
    q = c.of_type("quantitative")
    left = [n for n in q if c.colmeta(n).get("axis") == "left"]
    right = [n for n in q if c.colmeta(n).get("axis") == "right"]
    if left and right:
        c.enc.update(y_left=left[0], y_right=right[0])
    else:
        c.enc.update(y_left=q[0], y_right=q[1])
    c.used = [t, c.enc["y_left"], c.enc["y_right"]]
    return True


def _series(c):
    t, n, q = c.of_type("temporal", "x_axis"), c.of_type("nominal", "color_series"), c.of_type("quantitative", "y_axis")
    if not (t and n and q):
        return False
    c.enc = {"x": t[0], "series": n[0], "y": q[0]}
    c.dims, c.used = [t[0], n[0]], [t[0], n[0], q[0]]
    return True


def _scatter(c):
    q = c.of_type("quantitative", "x_axis")
    if len(q) < 2:
        return False
    c.enc = {"x": q[0], "y": q[1]}
    c.used = q[:2]
    return True


def _bubble(c):
    q = c.of_type("quantitative", "x_axis")
    if len(q) < 3:
        return False
    sz = [n for n in q if c.roles.get(n) == "size_or_secondary"]
    size = sz[0] if sz else q[2]
    xy = [n for n in q if n != size][:2]
    c.enc = {"x": xy[0], "y": xy[1], "size": size}
    c.used = [xy[0], xy[1], size]
    return True


# ------------------------------------------------------------------ value checks
def _no_missing(c):
    return not any(is_missing(v) for n in c.used for v in c.vals(n))


def _unique_dims(c):
    return c.unique_count(c.dims) == c.N


def _cap(c):
    return all(len(set(c.vals(n))) <= MAX_CAT for n in c.dims if c.cols[c.idx[n]]["type"] == "nominal")


def _additive(c):
    m = c.enc.get("value") or c.enc.get("y")
    return c.colmeta(m).get("additive") is True


def _nonneg(c):
    m = c.enc.get("value") or c.enc.get("y")
    return all(v >= 0 for v in c.vals(m))


def _grid(c):
    a, b = c.dims
    full = len(set(c.vals(a))) * len(set(c.vals(b))) == c.N
    return full or c.meta.get("missing_cells") in ("zero", "blank")


def _value_present(c):
    q = c.of_type("quantitative", "y_axis")
    if not q:
        return False
    c.enc["value"] = q[0]
    return not is_missing(c.vals(q[0])[0])


def _goal(c):
    g = c.meta.get("goal")
    if not isinstance(g, dict):
        return False
    if _isnum(g.get("value")) and "column" not in g:
        c.params["goal"] = float(g["value"])
        c.enc["goal"] = None
        return True
    col = g.get("column")
    if isinstance(col, str) and "value" not in g and col in c.idx and c.cols[c.idx[col]]["type"] == "quantitative" and c.N == 1 and _isnum(c.vals(col)[0]):
        c.params["goal"] = float(c.vals(col)[0])
        c.enc["goal"] = col
        return True
    return False


def _goal_bounds(c):
    b = c.meta["goal"].get("bounds")
    if not (isinstance(b, (list, tuple)) and len(b) == 2 and all(_isnum(x) for x in b) and b[0] < b[1]):
        return False
    c.enc["min"], c.enc["max"] = None, None
    c.params["min"], c.params["max"] = float(b[0]), float(b[1])
    return b[0] <= c.params["goal"] <= b[1]


def _in_bounds(c):
    v = float(c.vals(c.enc["value"])[0])
    return c.params["min"] <= v <= c.params["max"]


def _wf_order(c):
    w = c.meta.get("waterfall")
    o = w.get("order_by") if isinstance(w, dict) else None
    if not (isinstance(o, str) and o in c.idx):
        return False
    v = c.vals(o)
    if any(is_missing(x) for x in v) or len({repr(x) for x in v}) != len(v):
        return False
    c.enc["order_by"] = o
    return True


def _wf_total(c):
    t = c.meta["waterfall"].get("total")
    if not _isnum(t):
        return False
    c.params["total"] = float(t)
    return True


def _reconciles(c):
    s = _sum(float(v) for v in c.vals(c.enc["value"]))
    t = c.params["total"]
    c.params.update(sum=s, diff=s - t)
    return abs(s - t) <= 1e-6 + 1e-6 * abs(t)


def _slice_range(c):
    lo, hi = THRESHOLDS["donut_slices"]
    return lo <= c.N <= hi


def _pos_total(c):
    t = _sum(float(v) for v in c.vals(c.enc["value"]))
    c.params["total"] = t
    return t > 0


def _hier(c, depth):
    h = c.meta.get("hierarchy")
    lv = h.get("levels") if isinstance(h, dict) else None
    if not (isinstance(lv, list) and len(lv) >= depth and all(isinstance(x, str) and x in c.idx and c.cols[c.idx[x]]["type"] == "nominal" for x in lv) and len(set(lv)) == len(lv)):
        return False
    c.dims = list(lv)
    c.enc["levels"] = list(lv)
    return True


def _weight(c):
    w = c.meta["hierarchy"].get("weight")
    if not (isinstance(w, str) and w in c.idx and c.cols[c.idx[w]]["type"] == "quantitative"):
        return False
    c.enc["weight"] = w
    c.used = c.dims + [w]
    return True


def _leaf_cap(c):
    return c.N <= THRESHOLDS["treemap_max_leaves"]


# ------------------------------------------------------------------ raw-sample checks
def _raw_declared(c):
    r = c.meta.get("raw_samples")
    return r is True or isinstance(r, dict)


def _sample_col(c):
    r = c.meta.get("raw_samples")
    r = r if isinstance(r, dict) else {}
    q = c.of_type("quantitative", "y_axis")
    col = r.get("column")
    if col is None:
        if len(q) != 1:
            return False
        col = q[0]
    elif col not in q:
        return False
    g = r.get("group")
    if g is not None and not (isinstance(g, str) and g in c.idx and g != col and c.cols[c.idx[g]]["type"] == "nominal"):
        return False
    if c.output == "histogram":
        g = None  # a histogram pools all samples
    c.sample, c.group = col, g
    c.enc = {"value": col} if c.output == "histogram" else {"value": col, "group": g}
    return True


def _precomputed_ok(c):
    r = c.meta.get("raw_samples")
    r = r if isinstance(r, dict) else {}
    col = r.get("column") or (c.of_type("quantitative", "y_axis") or [None])[0]
    return c.colmeta(col).get("kind") not in ("bin", "quantile") if col else True


def _groups(c):
    """{group key: sorted finite samples}; rows with a missing measure are dropped."""
    vs = c.vals(c.sample)
    gs = c.vals(c.group) if c.group else [None] * c.N
    out = {}
    for v, g in zip(vs, gs):
        if not is_missing(v):
            out.setdefault(g if g is None else str(g), []).append(0.0 if float(v) == 0 else float(v))
    return {k: sorted(v) for k, v in sorted(out.items(), key=lambda kv: "" if kv[0] is None else kv[0])}


def _group_declared(c):
    return c.group is not None


def _two_groups(c):
    return len(_groups(c)) >= 2


def _group_complete(c):
    return not c.group or not any(is_missing(v) for v in c.vals(c.group))


def _group_cap(c):
    return len(_groups(c)) <= MAX_CAT


def _sd(x):
    m = _sum(x) / len(x)
    return math.sqrt(_sum((v - m) ** 2 for v in x) / (len(x) - 1))


def _min_hist(c):
    x = _groups(c).get(None, [])
    if len(x) < THRESHOLDS["min_samples_histogram"]:
        return False
    k = math.ceil(math.log2(len(x))) + 1
    c.params.update(n=len(x), bins=k, min=x[0], max=x[-1], width=(x[-1] - x[0]) / k)
    return True


def _min_violin(c):
    g = _groups(c)
    return bool(g) and all(len(x) >= THRESHOLDS["min_samples_violin"] for x in g.values())


def _non_const(c):
    g = _groups(c)
    if not all(x[0] != x[-1] for x in g.values()):
        return False
    if c.output == "violin":
        gl = []
        for k, x in g.items():
            sd, iqr = _sd(x), _quantile7(x, 0.75) - _quantile7(x, 0.25)
            s = min(sd, iqr / 1.34) if iqr > 0 else sd
            gl.append({"group": k, "n": len(x), "bandwidth": 0.9 * s * len(x) ** -0.2})
        c.params["groups"] = gl
    return True


def _min_box(c):
    g = _groups(c)
    if not g or not all(len(x) >= THRESHOLDS["min_group_boxplot"] for x in g.values()):
        return False
    gl = []
    for k, x in g.items():
        q1, med, q3 = _quantile7(x, 0.25), _quantile7(x, 0.5), _quantile7(x, 0.75)
        i = THRESHOLDS["boxplot_iqr_factor"] * (q3 - q1)
        inside = [v for v in x if q1 - i <= v <= q3 + i]
        gl.append({"group": k, "n": len(x), "q1": q1, "median": med, "q3": q3, "whisker_low": inside[0], "whisker_high": inside[-1],
                   "outliers": len(x) - len(inside)})
    c.params["groups"] = gl
    return True


# ------------------------------------------------------------------ dual axis, scatter, misc
def _dual_declared(c):
    return all(isinstance(c.meta.get("columns"), dict) and isinstance(c.meta["columns"].get(c.enc[k]), dict) for k in ("y_left", "y_right"))


def _units(c):
    return all(isinstance(c.colmeta(c.enc[k]).get("unit"), str) and c.colmeta(c.enc[k]).get("unit") for k in ("y_left", "y_right"))


def _axis_labels(c):
    return all(isinstance(c.colmeta(c.enc[k]).get("label"), str) and c.colmeta(c.enc[k]).get("label") for k in ("y_left", "y_right"))


def _axes_distinct(c):
    a, b = c.colmeta(c.enc["y_left"]).get("axis"), c.colmeta(c.enc["y_right"]).get("axis")
    return a == "left" and b == "right"


def _measures_distinct(c):
    return c.enc["y_left"] != c.enc["y_right"] and c.vals(c.enc["y_left"]) != c.vals(c.enc["y_right"])


def _min_pairs(c):
    return c.N >= THRESHOLDS["min_pairs_scatter"]


def _x_varies(c):
    return len(set(c.vals(c.enc["x"]))) > 1


def _size_nonneg(c):
    return all(v >= 0 for v in c.vals(c.enc["size"]))


def _size_unit(c):
    u = c.colmeta(c.enc["size"]).get("unit")
    return isinstance(u, str) and bool(u)


def _min_rows(c):
    return c.N >= THRESHOLDS["min_rows_line"]


CHECKS = {
    "base_eligible": lambda c: any(c.el.get(b) is True for b in c.carriers),
    "single_row": lambda c: c.N == 1,
    "value_present": _value_present,
    "goal_declared": _goal, "goal_bounds_valid": _goal_bounds, "value_within_bounds": _in_bounds,
    "cat_measure_shape": _shape_cat, "two_dim_shape": _shape_two, "time_shape": lambda c: _shape_time(c, 1), "series_shape": _series,
    "scatter_shape": _scatter, "bubble_shape": _bubble,
    "no_missing_used": _no_missing, "unique_categories": _unique_dims, "unique_pairs": _unique_dims, "unique_time": _unique_dims, "unique_paths": _unique_dims, "category_cap": _cap,
    "measure_additive": _additive, "nonnegative": _nonneg, "groups_disjoint": lambda c: c.flag("groups_disjoint"),
    "groups_exhaustive": lambda c: c.flag("groups_exhaustive"), "grid_or_missing_cells_declared": _grid,
    "order_declared": _wf_order, "total_declared": _wf_total, "reconciles": _reconciles,
    "slice_range": _slice_range, "positive_total": _pos_total,
    "hierarchy_declared": lambda c: _hier(c, 1), "hierarchy_depth_two": lambda c: _hier(c, 2), "weight_declared": _weight,
    "weight_additive": lambda c: c.colmeta(c.enc["weight"]).get("additive") is True,
    "weight_positive": lambda c: all(v > 0 for v in c.vals(c.enc["weight"])), "leaf_cap": _leaf_cap,
    "raw_samples_declared": _raw_declared, "not_precomputed": _precomputed_ok, "sample_column_resolved": _sample_col,
    "group_declared": _group_declared, "groups_min_two": _two_groups, "group_complete": _group_complete, "group_cap": _group_cap, "min_samples_histogram": _min_hist, "min_samples_violin": _min_violin,
    "min_group_boxplot": _min_box, "non_constant": _non_const,
    "min_rows_line": _min_rows, "min_pairs": _min_pairs, "x_varies": _x_varies, "size_nonnegative": _size_nonneg, "size_unit_declared": _size_unit,
    "dual_measures_declared": _dual_declared, "units_declared": _units, "axis_labels_declared": _axis_labels, "axes_distinct": _axes_distinct,
    "measures_distinct": _measures_distinct,
}
_DUAL = "combo_dual_axis"  # its `time_shape` precondition needs two measures (the id is shared with line/area)


def _heat_cap(c):
    return all(len(set(c.vals(n))) <= THRESHOLDS["heatmap_max_categories"] for n in c.dims)


CHECKS["heatmap_cap"] = _heat_cap


def _run(output, check_id, c):
    if output == _DUAL and check_id == "time_shape":
        return _shape_time(c, 2)
    return CHECKS[check_id](c)


def _carriers(output):
    return tuple(b for b, outs in SPECIALIZATION.items() if output in outs)


def _rank(base_scores):
    if base_scores is None:
        return list(BASE_CLASSES)
    sc = dict(zip(BASE_CLASSES, base_scores)) if isinstance(base_scores, (list, tuple)) else dict(base_scores)
    return sorted(BASE_CLASSES, key=lambda b: (-float(sc.get(b, float("-inf"))), BASE_CLASSES.index(b)))


def specialize_outputs(columns, rows, metadata=None, base_scores=None, roles=None, base_eligibility=None):
    """Choose the concrete output for a result set.

    columns: [{'name', 'type'}] (types resolved, see ``resolve_columns``); rows: equal-length lists; metadata: optional dict (see spec);
    base_scores: dict class->score or list aligned with BASE_CLASSES (absent: contract order); roles: optional {column: role};
    base_eligibility: dict class->bool from ``rules.eligible`` (required; a missing class counts as ineligible).
    Returns {output, encodings, params, rejected: [{output, reason_code}], fallback_chain}.
    """
    cols = resolve_columns(columns, rows)
    c = _Ctx(cols, rows, metadata, roles, base_eligibility or {})
    rejected, chain, seen = [], [], set()
    for base in _rank(base_scores):
        for out in SPECIALIZATION[base]:
            if out in seen:
                continue
            seen.add(out)
            chain.append(out)
            d = DEFINITIONS[out]
            c.reset()
            c.output = out
            c.carriers = _carriers(out)
            reason = None
            for p in d["preconditions"]:
                if not _run(out, p["id"], c):
                    reason = p["reason"]
                    break
            if reason is None:
                if out == "table":
                    c.enc = {"columns": [x["name"] for x in cols]}
                return {"output": out, "encodings": dict(c.enc), "params": c.params, "rejected": rejected, "fallback_chain": chain}
            rejected.append({"output": out, "reason_code": reason})
    raise AssertionError("table is always reachable")  # pragma: no cover
