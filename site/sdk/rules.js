// Rules-only baseline and hard semantic constraints over the 10 base classes (port of the Python/reference rules).
// Inputs are contract features only. Constraints are necessary data-side conditions; unknown semantics fail closed to `table`.
import { BASE_CLASSES, COLUMN_FEATURES, GLOBAL_FEATURES, SQL_FEATURES } from "./contract.js";
const T = {};
SQL_FEATURES.forEach(([n], i) => { T[n] = i; });
GLOBAL_FEATURES.forEach(([n], i) => { T[n] = 16 + i; });
const COL = {};
COLUMN_FEATURES.forEach(([n], i) => { COL[n] = i; });
const DONUT_MAX_K = 5, HEATMAP_MIN_K = 6, LONG_LABEL = 20 / 50, BAR_MAX_ROWS = 25, SCATTER_MIN_ROWS = 15;
function view(t, c) {
    const g = (n) => Number(t[T[n]]);
    return { single: g("single_row"), M: Math.round(g("column_count")), nom: Math.round(g("nominal_count")), quant: Math.round(g("quantitative_count")),
        temp: Math.round(g("temporal_count")), crossed: g("crossed_structure"), minK: g("min_nominal_cardinality"),
        rows: Math.round(10 ** g("log_row_count") - 1), // integer row count recovered from float32 log10(1+N)
        q: c.filter((r) => r[COL.is_quantitative] === 1), n: c.filter((r) => r[COL.is_nominal] === 1) };
}
export function rulePredict(t, c) {
    const v = view(t, c);
    const nonneg = v.q.length > 0 && v.q.every((r) => r[COL.negative_ratio] === 0);
    if (v.single === 1 && v.M <= 3 && v.quant >= 1)
        return "kpi";
    if (v.M >= 6)
        return "table";
    if (v.crossed === 1)
        return v.minK >= HEATMAP_MIN_K ? "heatmap" : "stacked_bar";
    if (v.M === 2 && v.temp === 1 && v.quant === 1)
        return nonneg ? "area" : "line";
    if (v.quant >= 2 && v.nom === 0 && v.temp === 0 && v.rows >= SCATTER_MIN_ROWS)
        return "scatter";
    if (v.M === 2 && v.nom === 1 && v.quant === 1) {
        const zeroAll = v.q.length > 0 && v.q.every((r) => r[COL.zero_ratio] === 1);
        if (v.minK <= DONUT_MAX_K && nonneg && !zeroAll)
            return "donut";
        if (v.n.length && v.n[0][COL.mean_string_length] >= LONG_LABEL)
            return "horizontal_bar";
        return v.rows <= BAR_MAX_ROWS ? "bar" : "table";
    }
    return "table";
}
export function eligible(t, c) {
    const v = view(t, c);
    const nonneg = v.q.length > 0 && v.q.every((r) => r[COL.negative_ratio] === 0);
    const positiveTotal = v.q.length > 0 && v.q.some((r) => r[COL.zero_ratio] < 1);
    const catMeasure = v.nom >= 1 && v.quant >= 1 && v.rows >= 2;
    return {
        kpi: v.single === 1 && v.quant >= 1 && v.M <= 3, bar: catMeasure, horizontal_bar: catMeasure,
        stacked_bar: v.nom >= 2 && v.quant >= 1 && nonneg && v.rows >= 4,
        line: v.temp >= 1 && v.quant >= 1 && v.rows >= 3, area: v.temp >= 1 && v.quant >= 1 && nonneg && v.rows >= 3,
        donut: v.nom >= 1 && v.quant >= 1 && nonneg && positiveTotal && v.minK >= 2 && v.minK <= 12,
        scatter: v.quant >= 2 && v.rows >= 3, heatmap: v.nom >= 2 && v.quant >= 1, table: true,
    };
}
/** Highest-scoring eligible class (stable on ties), else table. */
export function constrainedChoice(scores, t, c) {
    const el = eligible(t, c);
    const order = Array.from({ length: scores.length }, (_, k) => k).sort((a, b) => scores[b] - scores[a] || a - b);
    for (const k of order)
        if (el[BASE_CLASSES[k]])
            return { cls: BASE_CLASSES[k], changed: k !== order[0] };
    return { cls: "table", changed: true };
}
