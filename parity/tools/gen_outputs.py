#!/usr/bin/env python3
"""Fixtures for SqlVizSpec-Outputs-v1.0.0. Expected values come from the Python reference (packages/python/sqltoviz/outputs.py).
Usage: python parity/tools/gen_outputs.py [OUT=parity/outputs_v1.json] [--check]
Every positive case asserts the targeted output is chosen; every negative case asserts the targeted output is rejected with the stated
reason. Numeric params are compared by consumers at atol=rtol=1e-6. base_eligibility is computed here with the base rules and stored, so
ports consume it as an input and do not need the base pipeline to replay these cases."""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages" / "python"))
from sqltoviz import features as F, rules
from sqltoviz._contract import BASE_CLASSES
from sqltoviz._outputs import OUTPUTS, OUTPUTS_SHA256, OUTPUTS_VERSION, BASE_CONTRACT_SHA256, TOLERANCE
from sqltoviz.outputs import specialize_outputs, resolve_columns

CASES = []
DAYS = [f"2024-01-{d:02d}" for d in range(1, 29)]
CATS = ["North", "South", "East", "West", "Centro"]


def case(cid, kind, target, cols, rows, meta=None, top=None, roles=None, reason=None, note="", el=None):
    """kind: positive | negative | edge. top: base class ranked first (others in contract order)."""
    cols = [{"name": c} if isinstance(c, str) else c for c in cols]
    scores = None if top is None else {b: (1.0 if b == top else 0.0) for b in BASE_CLASSES}
    types = resolve_columns(cols, rows)
    if el is None:
        try:
            t, cm = F.extract("SELECT * FROM t", types, rows)
            el = rules.eligible(t, cm)
        except F.FeatureError:
            el = {b: b == "table" for b in BASE_CLASSES}
    c = {"id": cid, "kind": kind, "target": target, "note": note, "columns": types, "rows": rows, "metadata": meta, "base_scores": scores,
         "roles": roles, "base_eligibility": el}
    res = specialize_outputs(types, rows, meta, scores, roles, el)
    rej = {r["output"]: r["reason_code"] for r in res["rejected"]}
    if kind == "positive":
        assert res["output"] == target, (cid, res)
    elif kind == "negative":
        assert rej.get(target) == reason, (cid, target, reason, res)
    c["expected"] = {"output": res["output"], "encodings": res["encodings"], "params": res["params"], "rejected": res["rejected"],
                     "fallback_chain": res["fallback_chain"]}
    CASES.append(c)


def M(**kw):
    return kw


def cm(**kw):
    return {"columns": {k: v for k, v in kw.items()}}


# ---- kpi / gauge
case("kpi-pos", "positive", "kpi", ["revenue"], [[1234.5]], top="kpi")
case("kpi-pos-alias-note", "positive", "kpi", [{"name": "total_users"}, {"name": "label"}], [[42, "all"]], top="kpi", note="kpi_card is a legacy alias of kpi (aliases map)")
case("kpi-neg-two-rows", "negative", "kpi", ["revenue"], [[1.0], [2.0]], top="kpi", reason="base_ineligible")
case("kpi-edge-null-value", "edge", "kpi", ["revenue"], [[None]], top="kpi", note="all-missing column resolves to nominal; falls to table")
case("kpi-edge-empty", "edge", "kpi", ["revenue"], [], top="kpi", note="empty rows")
g = lambda **k: M(goal=k)
case("gauge-pos", "positive", "gauge", ["completion"], [[80.0]], g(value=100, bounds=[0, 150]), top="kpi")
case("gauge-pos-goal-column", "positive", "gauge", ["sales", "target"], [[80.0, 120.0]], g(column="target", bounds=[0, 200]), top="kpi")
case("gauge-neg-no-goal", "negative", "gauge", ["completion"], [[80.0]], None, top="kpi", reason="goal_missing")
case("gauge-neg-out-of-bounds", "negative", "gauge", ["completion"], [[180.0]], g(value=100, bounds=[0, 150]), top="kpi", reason="value_out_of_bounds")
case("gauge-neg-bad-bounds", "negative", "gauge", ["completion"], [[80.0]], g(value=100, bounds=[150, 0]), top="kpi", reason="goal_bounds_invalid")
case("gauge-neg-malformed-goal", "negative", "gauge", ["completion"], [[80.0]], {"goal": "100"}, top="kpi", reason="goal_missing", note="malformed metadata fails closed")
case("gauge-edge-value-null", "edge", "gauge", ["completion"], [[None]], g(value=100, bounds=[0, 150]), top="kpi")

# ---- bar family
sales = [[c, float(10 * (i + 1))] for i, c in enumerate(CATS)]
case("bar-pos", "positive", "bar", ["region", "sales"], sales, top="bar")
case("bar-pos-unicode", "positive", "bar", ["región", "ventas"], [["Ñandú", 3.0], ["日本", 5.0], ["emoji😀", 2.0]], top="bar", note="unicode labels")
case("bar-neg-duplicate-categories", "negative", "bar", ["region", "sales"], [["a", 1.0], ["a", 2.0], ["b", 3.0]], top="bar", reason="duplicate_categories")
case("bar-neg-too-many", "negative", "bar", ["region", "sales"], [[f"c{i}", float(i)] for i in range(26)], top="bar", reason="too_many_categories")
case("bar-edge-25-ok", "edge", "bar", ["region", "sales"], [[f"c{i}", float(i)] for i in range(25)], top="bar", note="exactly 25 categories is accepted")
case("bar-edge-huge-cardinality", "edge", "bar", ["region", "sales"], [[f"c{i}", float(i)] for i in range(300)], top="bar")
case("bar-edge-null-measure", "edge", "bar", ["region", "sales"], [["a", 1.0], ["b", None], ["c", 3.0]], top="bar")
case("bar-edge-single-row", "edge", "bar", ["region", "sales"], [["a", 1.0]], top="bar")
case("bar-edge-empty", "edge", "bar", ["region", "sales"], [], top="bar")
case("bar-edge-constant-measure", "edge", "bar", ["region", "sales"], [[c, 7.0] for c in CATS], top="bar")
case("bar-edge-mixed-types", "edge", "bar", ["region", "sales"], [["a", 1], ["b", "x"], ["c", 3.5]], top="bar", note="mixed-type measure resolves to nominal")
case("hbar-pos", "positive", "horizontal_bar", ["a_long_category_name", "sales"], [[f"a very long category label number {i}", float(i + 1)] for i in range(8)], top="horizontal_bar")
case("hbar-neg-duplicates", "negative", "horizontal_bar", ["region", "sales"], [["a", 1.0], ["a", 2.0], ["b", 3.0]], top="horizontal_bar", reason="duplicate_categories")
grid = [[r, p, float(i * 3 + j + 1)] for i, r in enumerate(["N", "S", "E"]) for j, p in enumerate(["x", "y", "z"])]
case("grouped-pos", "positive", "grouped_bar", ["region", "product", "sales"], grid, top="bar")
case("grouped-neg-duplicate-pairs", "negative", "grouped_bar", ["region", "product", "sales"], grid + [["N", "x", 9.0]], top="bar", reason="duplicate_groups")
case("grouped-neg-one-nominal", "negative", "grouped_bar", ["region", "sales"], sales, top="bar", reason="shape_mismatch")
add = cm(sales=dict(additive=True))
case("stacked-pos", "positive", "stacked_bar", ["region", "product", "sales"], grid, dict(columns={"sales": {"additive": True}}, groups_disjoint=True), top="stacked_bar")
case("stacked-neg-no-additive", "negative", "stacked_bar", ["region", "product", "sales"], grid, dict(groups_disjoint=True), top="stacked_bar", reason="additive_not_declared")
case("stacked-neg-not-disjoint", "negative", "stacked_bar", ["region", "product", "sales"], grid, dict(columns={"sales": {"additive": True}}), top="stacked_bar", reason="groups_not_disjoint")
case("stacked-neg-negative", "negative", "stacked_bar", ["region", "product", "sales"], grid[:-1] + [["E", "z", -1.0]], dict(columns={"sales": {"additive": True}}, groups_disjoint=True), top="stacked_bar", reason="base_ineligible")
case("stacked-neg-incomplete-grid", "negative", "stacked_bar", ["region", "product", "sales"], grid[:-1], dict(columns={"sales": {"additive": True}}, groups_disjoint=True), top="stacked_bar", reason="missing_cells_undeclared")
case("stacked-pos-missing-cells-declared", "positive", "stacked_bar", ["region", "product", "sales"], grid[:-1], dict(columns={"sales": {"additive": True}}, groups_disjoint=True, missing_cells="zero"), top="stacked_bar")
wf = [["start", 100.0], ["sales", 50.0], ["costs", -30.0], ["tax", -10.0]]
wfm = lambda total: dict(columns={"amount": {"additive": True}}, waterfall={"order_by": "step", "total": total})
case("waterfall-pos", "positive", "waterfall", ["step", "amount"], wf, wfm(110.0), top="bar")
case("waterfall-neg-reconcile", "negative", "waterfall", ["step", "amount"], wf, wfm(111.0), top="bar", reason="reconciliation_failed")
case("waterfall-neg-no-total", "negative", "waterfall", ["step", "amount"], wf, dict(columns={"amount": {"additive": True}}, waterfall={"order_by": "step"}), top="bar", reason="total_missing")
case("waterfall-neg-no-order", "negative", "waterfall", ["step", "amount"], wf, dict(columns={"amount": {"additive": True}}, waterfall={"total": 110.0}), top="bar", reason="order_missing")
case("waterfall-neg-not-additive", "negative", "waterfall", ["step", "amount"], wf, dict(waterfall={"order_by": "step", "total": 110.0}), top="bar", reason="additive_not_declared")
case("waterfall-edge-tolerance", "edge", "waterfall", ["step", "amount"], [["a", 0.1], ["b", 0.2]], dict(columns={"amount": {"additive": True}}, waterfall={"order_by": "step", "total": 0.3}), top="bar", note="0.1+0.2 vs 0.3 within 1e-6")

# ---- line / area / dual axis
line = [[DAYS[i], float(i * i)] for i in range(6)]
case("line-pos", "positive", "line", ["day", "visits"], line, top="line")
case("line-neg-duplicate-x", "negative", "line", ["day", "visits"], line + [[DAYS[0], 3.0]], top="line", reason="duplicate_x")
case("line-neg-two-rows", "negative", "line", ["day", "visits"], line[:2], top="line", reason="base_ineligible")
case("line-edge-null", "edge", "line", ["day", "visits"], line[:3] + [[DAYS[7], None]], top="line")
case("line-edge-rfc3339", "edge", "line", ["ts", "visits"], [["2024-01-01T00:00:00Z", 1.0], ["2024-01-01T12:00:00+01:00", 2.0], ["2024-01-02T00:00:00Z", 3.0]], top="line")
dual = [[DAYS[i], float(100 + i), float(1e9 * (i + 1))] for i in range(6)]
dm = lambda **o: {"columns": {"revenue": {**dict(unit="USD", axis="left", label="Revenue (USD)"), **o.get("rev", {})}, "visits": {**dict(unit="count", axis="right", label="Visits"), **o.get("vis", {})}}}
case("dual-pos", "positive", "combo_dual_axis", ["day", "revenue", "visits"], dual, dm(), top="line")
case("dual-pos-scale-ratio-ignored", "positive", "combo_dual_axis", ["day", "revenue", "visits"], dual, dm(), top="line", note="the 1e7 scale ratio is never inspected")
case("dual-neg-no-unit", "negative", "combo_dual_axis", ["day", "revenue", "visits"], dual, {"columns": {"revenue": {"axis": "left", "label": "R"}, "visits": {"axis": "right", "unit": "n", "label": "V"}}}, top="line", reason="unit_missing")
case("dual-neg-no-label", "negative", "combo_dual_axis", ["day", "revenue", "visits"], dual, {"columns": {"revenue": {"axis": "left", "unit": "USD"}, "visits": {"axis": "right", "unit": "n", "label": "V"}}}, top="line", reason="axis_label_missing")
case("dual-neg-same-axis", "negative", "combo_dual_axis", ["day", "revenue", "visits"], dual, dm(vis={"axis": "left"}), top="line", reason="axes_not_distinct")
case("dual-neg-identical-measures", "negative", "combo_dual_axis", ["day", "revenue", "visits"], [[d, v, v] for d, v, _ in dual], dm(), top="line", reason="measures_identical")
case("dual-neg-no-metadata", "negative", "combo_dual_axis", ["day", "revenue", "visits"], dual, None, top="line", reason="measures_not_declared")
case("dual-neg-one-measure", "negative", "combo_dual_axis", ["day", "revenue"], line, None, top="line", reason="shape_mismatch")
case("area-pos", "positive", "area", ["day", "visits"], line, top="area")
case("area-neg-negative", "negative", "area", ["day", "visits"], line[:5] + [[DAYS[9], -4.0]], top="area", reason="base_ineligible")
sa = [[DAYS[d], s, float(d + 1 + j)] for d in range(4) for j, s in enumerate(["web", "app"])]
sam = dict(columns={"sessions": {"additive": True}}, groups_disjoint=True)
case("stacked-area-pos", "positive", "stacked_area", ["day", "channel", "sessions"], sa, sam, top="area")
case("stacked-area-neg-not-additive", "negative", "stacked_area", ["day", "channel", "sessions"], sa, dict(groups_disjoint=True), top="area", reason="additive_not_declared")
case("stacked-area-neg-duplicates", "negative", "stacked_area", ["day", "channel", "sessions"], sa + [[DAYS[0], "web", 1.0]], sam, top="area", reason="duplicate_groups")
case("stacked-area-neg-incomplete", "negative", "stacked_area", ["day", "channel", "sessions"], sa[:-1], sam, top="area", reason="missing_cells_undeclared")

# ---- donut / hierarchy
parts = [["a", 40.0], ["b", 30.0], ["c", 20.0], ["d", 10.0]]
dn = dict(columns={"share": {"additive": True}}, groups_disjoint=True, groups_exhaustive=True)
case("donut-pos", "positive", "donut", ["slice", "share"], parts, dn, top="donut")
case("donut-neg-not-exhaustive", "negative", "donut", ["slice", "share"], parts, dict(columns={"share": {"additive": True}}, groups_disjoint=True), top="donut", reason="groups_not_exhaustive")
case("donut-neg-overlap", "negative", "donut", ["slice", "share"], parts, dict(columns={"share": {"additive": True}}, groups_exhaustive=True), top="donut", reason="groups_not_disjoint")
case("donut-neg-not-additive", "negative", "donut", ["slice", "share"], parts, dict(groups_disjoint=True, groups_exhaustive=True), top="donut", reason="additive_not_declared")
case("donut-neg-too-many-slices", "negative", "donut", ["slice", "share"], [[f"s{i}", 1.0] for i in range(13)], dn, top="donut", reason="base_ineligible")
case("donut-neg-negative", "negative", "donut", ["slice", "share"], parts[:3] + [["d", -1.0]], dn, top="donut", reason="base_ineligible")
case("donut-edge-zero-total", "edge", "donut", ["slice", "share"], [["a", 0.0], ["b", 0.0]], dn, top="donut")
h2 = [[r, p, float(i * 2 + j + 1)] for i, r in enumerate(["N", "S"]) for j, p in enumerate(["x", "y"])]
hm = lambda lv: dict(hierarchy={"levels": lv, "weight": "sales"}, columns={"sales": {"additive": True}}, groups_disjoint=True)
case("sunburst-pos", "positive", "sunburst", ["region", "product", "sales"], h2, hm(["region", "product"]), top="donut")
case("sunburst-neg-shallow", "negative", "sunburst", ["region", "product", "sales"], h2, hm(["region"]), top="donut", reason="hierarchy_too_shallow")
case("sunburst-neg-no-hierarchy", "negative", "sunburst", ["region", "product", "sales"], h2, dict(columns={"sales": {"additive": True}}, groups_disjoint=True), top="donut", reason="hierarchy_missing")
case("treemap-pos", "positive", "treemap", ["region", "sales"], [["N", 4.0], ["S", 3.0], ["E", 2.0]], hm(["region"]), top="donut", note="one level: sunburst needs two, so it is rejected first (donut base)")
case("treemap-pos-three-level-via-bar", "positive", "treemap", ["region", "product", "sku", "sales"], [[r, p, f"k{k}", float(i + j + k + 1)] for i, r in enumerate(["N", "S"]) for j, p in enumerate(["x", "y"]) for k in range(2)], dict(hierarchy={"levels": ["region", "product", "sku"], "weight": "sales"}, columns={"sales": {"additive": True}}, groups_disjoint=True), top="bar", note="grouped_bar fails on duplicate (region,product) pairs")
case("treemap-neg-weight-not-additive", "negative", "treemap", ["region", "product", "sales"], h2, dict(hierarchy={"levels": ["region", "product"], "weight": "sales"}, groups_disjoint=True), top="donut", reason="weight_not_additive")
case("treemap-neg-nonpositive-weight", "negative", "treemap", ["region", "product", "sales"], h2[:3] + [["S", "y", 0.0]], hm(["region", "product"]), top="donut", reason="non_positive_weight")
case("treemap-neg-duplicate-paths", "negative", "treemap", ["region", "product", "sales"], h2 + [["N", "x", 1.0]], hm(["region", "product"]), top="donut", reason="duplicate_paths")
case("treemap-neg-weight-missing", "negative", "treemap", ["region", "product", "sales"], h2, dict(hierarchy={"levels": ["region", "product"]}, groups_disjoint=True), top="donut", reason="weight_missing")
case("treemap-neg-not-disjoint", "negative", "treemap", ["region", "product", "sales"], h2, dict(hierarchy={"levels": ["region", "product"], "weight": "sales"}, columns={"sales": {"additive": True}}), top="donut", reason="groups_not_disjoint")

# ---- scatter / bubble / heatmap
pts = [[float(i), float(i * i % 7), float(i % 4 + 1)] for i in range(8)]
case("scatter-pos", "positive", "scatter", ["x", "y"], [r[:2] for r in pts], top="scatter")
case("scatter-neg-constant-x", "negative", "scatter", ["x", "y"], [[1.0, float(i)] for i in range(8)], top="scatter", reason="constant_values")
case("scatter-neg-two-rows", "negative", "scatter", ["x", "y"], pts[:2] and [r[:2] for r in pts[:2]], top="scatter", reason="base_ineligible")
case("scatter-edge-null", "edge", "scatter", ["x", "y"], [[1.0, 2.0], [2.0, None], [3.0, 4.0], [4.0, 5.0]], top="scatter")
bm = {"columns": {"size": {"unit": "people"}}}
case("bubble-pos", "positive", "bubble", ["x", "y", "size"], pts, bm, top="scatter")
case("bubble-neg-no-unit", "negative", "bubble", ["x", "y", "size"], pts, None, top="scatter", reason="unit_missing")
case("bubble-neg-negative-size", "negative", "bubble", ["x", "y", "size"], pts[:7] + [[7.0, 2.0, -3.0]], bm, top="scatter", reason="negative_values")
case("bubble-neg-two-measures", "negative", "bubble", ["x", "y"], [r[:2] for r in pts], bm, top="scatter", reason="shape_mismatch")
case("heatmap-pos", "positive", "heatmap", ["row", "col", "n"], [[r, c, float(i + j)] for i, r in enumerate("abcdefg") for j, c in enumerate("uvwxyz")], top="heatmap")
case("heatmap-neg-duplicate", "negative", "heatmap", ["row", "col", "n"], [[r, c, 1.0] for r in "ab" for c in "uv"] + [["a", "u", 2.0]], top="heatmap", reason="duplicate_groups")
case("heatmap-neg-missing-cells", "negative", "heatmap", ["row", "col", "n"], [[r, c, 1.0] for r in "ab" for c in "uv"][:3], top="heatmap", reason="missing_cells_undeclared")
case("heatmap-pos-missing-cells-declared", "positive", "heatmap", ["row", "col", "n"], [[r, c, 1.0] for r in "ab" for c in "uv"][:3], dict(missing_cells="blank"), top="heatmap")
case("heatmap-neg-too-many", "negative", "heatmap", ["row", "col", "n"], [[f"r{i}", f"c{j}", 1.0] for i in range(51) for j in range(2)], top="heatmap", reason="too_many_categories")

# ---- distributions (raw samples)
S = lambda n, off=0.0: [float((i * 37 + 11) % 101) / 10 + off for i in range(n)]
raw = dict(raw_samples={"column": "latency"})
rawg = dict(raw_samples={"column": "latency", "group": "service"})
two = lambda n1, n2, k: [[ "api", v] for v in S(n1)] + [["db", v + 5] for v in S(n2)]
case("histogram-pos", "positive", "histogram", ["latency"], [[v] for v in S(60)], raw, top="bar")
case("histogram-pos-single-group-pooled", "positive", "histogram", ["service", "latency"], [["api", v] for v in S(45)], rawg, top="bar", note="one declared group: violin/boxplot need two groups, histogram pools")
case("histogram-neg-too-few", "negative", "histogram", ["latency"], [[v] for v in S(29)], raw, top="bar", reason="too_few_samples")
case("histogram-neg-constant", "negative", "histogram", ["latency"], [[5.0]] * 40, raw, top="bar", reason="constant_values")
case("histogram-neg-not-declared", "negative", "histogram", ["latency"], [[v] for v in S(60)], None, top="bar", reason="raw_samples_not_declared")
case("histogram-neg-prebinned", "negative", "histogram", ["latency"], [[v] for v in S(60)], dict(raw_samples={"column": "latency"}, columns={"latency": {"kind": "bin"}}), top="bar", reason="precomputed_input")
case("histogram-neg-ambiguous-column", "negative", "histogram", ["a", "b"], [[v, v] for v in S(60)], dict(raw_samples=True), top="bar", reason="column_ambiguous")
case("histogram-edge-nulls-dropped", "edge", "histogram", ["latency"], [[v] for v in S(40)] + [[None]] * 5, raw, top="bar")
case("histogram-edge-boundary-30", "edge", "histogram", ["latency"], [[v] for v in S(30)], raw, top="bar", note="exactly 30 samples accepted; bins = ceil(log2 30)+1 = 6")
case("histogram-edge-unicode-name", "edge", "histogram", ["latencia_ms"], [[v] for v in S(35)], dict(raw_samples={"column": "latencia_ms"}), top="bar")
case("boxplot-pos", "positive", "boxplot", ["service", "latency"], two(8, 9, 0), rawg, top="bar")
case("boxplot-pos-boundary-5", "positive", "boxplot", ["service", "latency"], two(5, 5, 0), rawg, top="bar")
case("boxplot-pos-outlier", "positive", "boxplot", ["service", "latency"], [["api", v] for v in [1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 100.0]] + [["db", v] for v in S(6)], rawg, top="bar", note="Tukey whisker excludes 100")
case("boxplot-neg-small-group", "negative", "boxplot", ["service", "latency"], two(8, 4, 0), rawg, top="bar", reason="group_too_small")
case("boxplot-neg-no-group", "negative", "boxplot", ["latency"], [[v] for v in S(10)], raw, top="bar", reason="group_required")
case("boxplot-neg-not-declared", "negative", "boxplot", ["service", "latency"], two(8, 9, 0), None, top="bar", reason="raw_samples_not_declared")
case("boxplot-neg-too-many-groups", "negative", "boxplot", ["service", "latency"], [[f"g{i}", float(j)] for i in range(26) for j in range(5)], rawg, top="bar", reason="too_many_categories")
case("boxplot-neg-null-group", "negative", "boxplot", ["service", "latency"], two(8, 9, 0) + [[None, 1.0]], rawg, top="bar", reason="missing_values")
case("violin-pos", "positive", "violin", ["service", "latency"], two(40, 35, 0), rawg, top="bar")
case("violin-neg-few-samples", "negative", "violin", ["service", "latency"], two(40, 29, 0), rawg, top="bar", reason="too_few_samples")
case("violin-neg-constant-group", "negative", "violin", ["service", "latency"], [["api", v] for v in S(40)] + [["db", 3.0]] * 35, rawg, top="bar", reason="constant_values")
case("violin-neg-single-group", "negative", "violin", ["service", "latency"], [["api", v] for v in S(40)], rawg, top="bar", reason="group_required")
case("violin-neg-prebinned", "negative", "violin", ["service", "latency"], two(40, 35, 0), dict(rawg, columns={"latency": {"kind": "quantile"}}), top="bar", reason="precomputed_input")
case("violin-edge-iqr-zero", "edge", "violin", ["service", "latency"], [["api", 1.0]] * 34 + [["api", 9.0]] + [["db", v] for v in S(35)], rawg, top="bar", note="IQR 0: Silverman falls back to sd")

# ---- table + cross-cutting edges
case("table-pos", "positive", "table", ["a", "b", "c", "d", "e", "f"], [[1, "x", 2, "y", 3, "z"]] * 3, top="table")
case("table-edge-everything-missing", "edge", "table", ["a", "b"], [[None, None], ["", None]], top="table")
case("edge-fallback-no-top-bar-fails", "edge", "table", ["region", "sales"], [["a", 1.0], ["a", 2.0]], top="bar", note="all candidates rejected: terminal table")
case("edge-no-scores-contract-order", "edge", "bar", ["region", "sales"], sales, None, note="absent base_scores: contract order")
case("edge-ineligible-everything", "edge", "table", ["region", "sales"], sales, None, el={b: b == "table" for b in BASE_CLASSES}, note="nothing eligible: raw outputs still need declared samples")
case("edge-roles-ignored-column", "edge", "bar", ["region", "tooltip", "sales"], [[c, "t", float(i)] for i, c in enumerate(CATS)], top="bar", roles={"tooltip": "ignore_tooltip"})
case("edge-metadata-wrong-types", "edge", "gauge", ["completion"], [[80.0]], {"goal": {"value": "x", "bounds": "no"}, "columns": [], "raw_samples": 3}, top="kpi")


def build():
    per = {o: {"positive": 0, "negative": 0, "edge": 0} for o in OUTPUTS}
    for c in CASES:
        per[c["target"]][c["kind"]] += 1
    missing = [o for o in OUTPUTS if per[o]["positive"] == 0 or per[o]["negative"] + per[o]["edge"] == 0]
    assert not missing, f"outputs lacking positive or negative/edge coverage: {missing}"
    assert len({c["id"] for c in CASES}) == len(CASES)
    return {"fixture_version": "outputs-v1", "outputs_version": OUTPUTS_VERSION, "outputs_sha256": OUTPUTS_SHA256, "base_contract_sha256": BASE_CONTRACT_SHA256,
            "atol": TOLERANCE["atol"], "rtol": TOLERANCE["rtol"], "n_cases": len(CASES), "support_per_output": per, "cases": CASES}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = Path(args[0]) if args else ROOT / "parity" / "outputs_v1.json"
    text = json.dumps(build(), indent=1, ensure_ascii=False, sort_keys=False) + "\n"
    if "--check" in sys.argv:
        if not out.exists() or out.read_text() != text:
            sys.exit(f"{out} is stale: rerun python parity/tools/gen_outputs.py")
        print("ok:", out)
    else:
        out.write_text(text)
        print("wrote", out, len(CASES), "cases")
