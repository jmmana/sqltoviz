// SqlVizSpec-Outputs-v1.0.0 TypeScript port of packages/python/sqltoviz/outputs.py (additive extension; the base contract is untouched).
// Preconditions run in the order the spec lists them; the first failing one is the rejection reason. Absent or malformed metadata fails closed.
import {isMissing, parseTemporal, resolveType, type Cell, type ColumnSpec} from "./features.js";
import {BASE_CLASSES} from "./contract.js";
import {ALIASES, DEFINITIONS, SPECIALIZATION, THRESHOLDS} from "./outputs-contract.js";

const T: any = THRESHOLDS;
const MAX_CAT: number = T.max_categories_bar;

export interface OutputsResult { output: string; encodings: Record<string, any>; params: Record<string, any>; rejected: {output: string; reason_code: string}[]; fallback_chain: string[] }
export interface ResolvedColumn { name: string; type: string }

/** Map legacy aliases (`kpi_card`) to the canonical output name. */
export function normalizeOutput(name: string): string { return ALIASES[name] ?? name; }

/** Resolve column types with the base contract rules (explicit `type` honoured, else inferred). */
export function resolveColumns(columns: (string | ColumnSpec)[], rows: Cell[][]): ResolvedColumn[] {
  return columns.map((c, j) => {
    const spec: ColumnSpec = typeof c === "string" ? {name: c} : c;
    return {name: spec.name, type: resolveType(spec.name, rows.map((r) => r[j]), spec.type ?? undefined)};
  });
}

const isNum = (x: unknown): x is number => typeof x === "number" && Number.isFinite(x);
const isDict = (x: unknown): x is Record<string, any> => typeof x === "object" && x !== null && !Array.isArray(x);
const has = (o: Record<string, any>, k: string) => Object.prototype.hasOwnProperty.call(o, k);
const get = (o: any, k: string): any => (isDict(o) && has(o, k) ? o[k] : undefined);
const isStr = (x: unknown): x is string => typeof x === "string";
const sum = (v: Iterable<number>) => { let a = 0; for (const x of v) a += x; return a; };
const quantile7 = (s: number[], p: number) => { const n = s.length, h = (n - 1) * p, lo = Math.floor(h), hi = Math.min(lo + 1, n - 1); return s[lo] + (h - lo) * (s[hi] - s[lo]); };
const sd = (x: number[]) => { const m = sum(x) / x.length; return Math.sqrt(sum(x.map((v) => (v - m) ** 2)) / (x.length - 1)); };
const cmpCp = (a: string, b: string) => { const x = Array.from(a), y = Array.from(b); for (let i = 0; i < Math.min(x.length, y.length); i++) { const d = x[i].codePointAt(0)! - y[i].codePointAt(0)!; if (d) return d; } return x.length - y.length; };
const pyStr = (v: unknown): string => v === null || v === undefined ? "None" : v === true ? "True" : v === false ? "False" : String(v);
const key = (v: unknown) => JSON.stringify(v === null || v === undefined ? ["z"] : [typeof v, v]);

class Ctx {
  N: number; idx = new Map<string, number>(); meta: Record<string, any>; roles: Record<string, any>;
  enc: Record<string, any> = {}; params: Record<string, any> = {}; used: string[] = []; dims: string[] = [];
  sample: string | null = null; group: string | null = null; output = ""; carriers: string[] = [];
  constructor(public cols: ResolvedColumn[], public rows: any[][], meta: unknown, roles: unknown, public el: Record<string, any>) {
    this.N = rows.length; this.meta = isDict(meta) ? meta : {}; this.roles = isDict(roles) ? roles : {};
    cols.forEach((c, j) => this.idx.set(c.name, j));
  }
  reset() { this.enc = {}; this.params = {}; this.used = []; this.dims = []; this.sample = null; this.group = null; this.output = ""; this.carriers = []; }
  vals(n: string): any[] { const j = this.idx.get(n)!; return this.rows.map((r) => r[j]); }
  type(n: string) { return this.cols[this.idx.get(n)!].type; }
  ofType(t: string, role?: string, exclude: string[] = []): string[] {
    let c = this.cols.filter((x) => x.type === t && !exclude.includes(x.name) && this.roles[x.name] !== "ignore_tooltip").map((x) => x.name);
    if (role) { const pref = c.filter((n) => this.roles[n] === role); c = [...pref, ...c.filter((n) => !pref.includes(n))]; }
    return c;
  }
  colmeta(n: string): Record<string, any> { const m = get(this.meta, "columns"); const v = get(m, n); return isDict(v) ? v : {}; }
  flag(k: string) { return this.meta[k] === true; }
  k(n: string, v: unknown) { return this.type(n) === "temporal" ? ["t", parseTemporal(v)] : isNum(v) ? ["n", v === 0 ? 0 : v] : key(v); }
  uniqueCount(names: string[]) { const cols = names.map((n) => this.vals(n)); const s = new Set<string>(); for (let i = 0; i < this.N; i++) s.add(JSON.stringify(names.map((n, j) => this.k(n, cols[j][i])))); return s.size; }
}
type C = Ctx;

const shapeCat = (c: C) => {
  const n = c.ofType("nominal", "x_axis"), q = c.ofType("quantitative", "y_axis");
  if (!n.length || !q.length) return false;
  c.enc = {category: n[0], value: q[0]}; c.dims = [n[0]]; c.used = [n[0], q[0]]; return true;
};
const shapeTwo = (c: C) => {
  const n = c.ofType("nominal", "x_axis"), q = c.ofType("quantitative", "y_axis");
  if (n.length < 2 || !q.length) return false;
  const cat = n[0], ser = c.ofType("nominal", "color_series", [cat])[0];
  c.enc = c.output === "heatmap" ? {row: cat, column: ser, value: q[0]} : {category: cat, series: ser, value: q[0]};
  c.dims = [cat, ser]; c.used = [cat, ser, q[0]]; return true;
};
const shapeDual = (c: C, t: string) => {
  c.enc = {x: t}; c.dims = [t];
  const q = c.ofType("quantitative"), left = q.filter((n) => c.colmeta(n).axis === "left"), right = q.filter((n) => c.colmeta(n).axis === "right");
  if (left.length && right.length) { c.enc.y_left = left[0]; c.enc.y_right = right[0]; } else { c.enc.y_left = q[0]; c.enc.y_right = q[1]; }
  c.used = [t, c.enc.y_left, c.enc.y_right]; return true;
};
const shapeTime = (c: C, wantQ = 1) => {
  const t = c.ofType("temporal", "x_axis"), q = c.ofType("quantitative", "y_axis");
  if (!t.length || q.length < wantQ) return false;
  if (wantQ === 2) return shapeDual(c, t[0]);
  c.enc = {x: t[0], y: q[0]}; c.dims = [t[0]]; c.used = [t[0], q[0]]; return true;
};
const series = (c: C) => {
  const t = c.ofType("temporal", "x_axis"), n = c.ofType("nominal", "color_series"), q = c.ofType("quantitative", "y_axis");
  if (!(t.length && n.length && q.length)) return false;
  c.enc = {x: t[0], series: n[0], y: q[0]}; c.dims = [t[0], n[0]]; c.used = [t[0], n[0], q[0]]; return true;
};
const scatter = (c: C) => {
  const q = c.ofType("quantitative", "x_axis"); if (q.length < 2) return false;
  c.enc = {x: q[0], y: q[1]}; c.used = q.slice(0, 2); return true;
};
const bubble = (c: C) => {
  const q = c.ofType("quantitative", "x_axis"); if (q.length < 3) return false;
  const sz = q.filter((n) => c.roles[n] === "size_or_secondary"), size = sz.length ? sz[0] : q[2], xy = q.filter((n) => n !== size).slice(0, 2);
  c.enc = {x: xy[0], y: xy[1], size}; c.used = [xy[0], xy[1], size]; return true;
};

const noMissing = (c: C) => !c.used.some((n) => c.vals(n).some(isMissing));
const uniqueDims = (c: C) => c.uniqueCount(c.dims) === c.N;
const cap = (c: C) => c.dims.every((n) => c.type(n) !== "nominal" || new Set(c.vals(n).map(key)).size <= MAX_CAT);
const measure = (c: C) => c.enc.value ?? c.enc.y;
const additive = (c: C) => c.colmeta(measure(c)).additive === true;
const nonneg = (c: C) => c.vals(measure(c)).every((v) => v >= 0);
const grid = (c: C) => {
  const [a, b] = c.dims; const full = new Set(c.vals(a).map(key)).size * new Set(c.vals(b).map(key)).size === c.N;
  return full || c.meta.missing_cells === "zero" || c.meta.missing_cells === "blank";
};
const valuePresent = (c: C) => {
  const q = c.ofType("quantitative", "y_axis"); if (!q.length) return false;
  c.enc.value = q[0]; return !isMissing(c.vals(q[0])[0]);
};
const goal = (c: C) => {
  const g = c.meta.goal; if (!isDict(g)) return false;
  if (isNum(g.value) && !has(g, "column")) { c.params.goal = g.value; c.enc.goal = null; return true; }
  const col = g.column;
  if (isStr(col) && !has(g, "value") && c.idx.has(col) && c.type(col) === "quantitative" && c.N === 1 && isNum(c.vals(col)[0])) { c.params.goal = c.vals(col)[0]; c.enc.goal = col; return true; }
  return false;
};
const goalBounds = (c: C) => {
  const b = c.meta.goal.bounds;
  if (!(Array.isArray(b) && b.length === 2 && b.every(isNum) && b[0] < b[1])) return false;
  c.enc.min = null; c.enc.max = null; c.params.min = b[0]; c.params.max = b[1];
  return b[0] <= c.params.goal && c.params.goal <= b[1];
};
const inBounds = (c: C) => { const v = c.vals(c.enc.value)[0]; return c.params.min <= v && v <= c.params.max; };
const wfOrder = (c: C) => {
  const o = get(c.meta.waterfall, "order_by");
  if (!(isStr(o) && c.idx.has(o))) return false;
  const v = c.vals(o);
  if (v.some(isMissing) || new Set(v.map(key)).size !== v.length) return false;
  c.enc.order_by = o; return true;
};
const wfTotal = (c: C) => { const t = c.meta.waterfall.total; if (!isNum(t)) return false; c.params.total = t; return true; };
const reconciles = (c: C) => {
  const s = sum(c.vals(c.enc.value).map(Number)), t = c.params.total;
  c.params.sum = s; c.params.diff = s - t; return Math.abs(s - t) <= 1e-6 + 1e-6 * Math.abs(t);
};
const sliceRange = (c: C) => T.donut_slices[0] <= c.N && c.N <= T.donut_slices[1];
const posTotal = (c: C) => { const t = sum(c.vals(c.enc.value).map(Number)); c.params.total = t; return t > 0; };
const hier = (c: C, depth: number) => {
  const lv = get(c.meta.hierarchy, "levels");
  if (!(Array.isArray(lv) && lv.length >= depth && lv.every((x) => isStr(x) && c.idx.has(x) && c.type(x) === "nominal") && new Set(lv).size === lv.length)) return false;
  c.dims = [...lv]; c.enc.levels = [...lv]; return true;
};
const weight = (c: C) => {
  const w = c.meta.hierarchy.weight;
  if (!(isStr(w) && c.idx.has(w) && c.type(w) === "quantitative")) return false;
  c.enc.weight = w; c.used = [...c.dims, w]; return true;
};
const rawDeclared = (c: C) => c.meta.raw_samples === true || isDict(c.meta.raw_samples);
const sampleCol = (c: C) => {
  const r = isDict(c.meta.raw_samples) ? c.meta.raw_samples : {}, q = c.ofType("quantitative", "y_axis");
  let col = r.column; const hasCol = col !== undefined && col !== null;
  if (!hasCol) { if (q.length !== 1) return false; col = q[0]; } else if (!q.includes(col)) return false;
  let g = r.group === undefined ? null : r.group;
  if (g !== null && !(isStr(g) && c.idx.has(g) && g !== col && c.type(g) === "nominal")) return false;
  if (c.output === "histogram") g = null;
  c.sample = col; c.group = g;
  c.enc = c.output === "histogram" ? {value: col} : {value: col, group: g}; return true;
};
const precomputedOk = (c: C) => {
  const r = isDict(c.meta.raw_samples) ? c.meta.raw_samples : {};
  const col = r.column || c.ofType("quantitative", "y_axis")[0] || null;
  if (!col) return true;
  const k = c.colmeta(col).kind; return k !== "bin" && k !== "quantile";
};
/** [group key, sorted finite samples] pairs sorted by key; rows with a missing measure are dropped. The no-group key is null. */
const groups = (c: C): [string | null, number[]][] => {
  const vs = c.vals(c.sample!), gs = c.group ? c.vals(c.group) : vs.map(() => null), out = new Map<string | null, number[]>();
  vs.forEach((v, i) => {
    if (isMissing(v)) return;
    const k = c.group ? pyStr(gs[i]) : null, x = Number(v) === 0 ? 0 : Number(v);
    if (!out.has(k)) out.set(k, []);
    out.get(k)!.push(x);
  });
  return [...out.entries()].sort((a, b) => cmpCp(a[0] ?? "", b[0] ?? "")).map(([k, v]) => [k, v.sort((x, y) => x - y)]);
};
const minHist = (c: C) => {
  const x = groups(c).find(([k]) => k === null)?.[1] ?? [];
  if (x.length < T.min_samples_histogram) return false;
  const k = Math.ceil(Math.log2(x.length)) + 1;
  Object.assign(c.params, {n: x.length, bins: k, min: x[0], max: x[x.length - 1], width: (x[x.length - 1] - x[0]) / k}); return true;
};
const nonConst = (c: C) => {
  const g = groups(c);
  if (!g.every(([, x]) => x[0] !== x[x.length - 1])) return false;
  if (c.output === "violin") {
    c.params.groups = g.map(([k, x]) => {
      const s0 = sd(x), iqr = quantile7(x, 0.75) - quantile7(x, 0.25), s = iqr > 0 ? Math.min(s0, iqr / 1.34) : s0;
      return {group: k, n: x.length, bandwidth: 0.9 * s * Math.pow(x.length, -0.2)};
    });
  }
  return true;
};
const minBox = (c: C) => {
  const g = groups(c);
  if (!g.length || !g.every(([, x]) => x.length >= T.min_group_boxplot)) return false;
  c.params.groups = g.map(([k, x]) => {
    const q1 = quantile7(x, 0.25), med = quantile7(x, 0.5), q3 = quantile7(x, 0.75), i = T.boxplot_iqr_factor * (q3 - q1);
    const inside = x.filter((v) => q1 - i <= v && v <= q3 + i);
    return {group: k, n: x.length, q1, median: med, q3, whisker_low: inside[0], whisker_high: inside[inside.length - 1], outliers: x.length - inside.length};
  });
  return true;
};
const both = (c: C, f: (m: Record<string, any>) => boolean) => ["y_left", "y_right"].every((k) => f(c.colmeta(c.enc[k])));
const nonEmptyStr = (x: unknown) => isStr(x) && x.length > 0;
const dualDeclared = (c: C) => ["y_left", "y_right"].every((k) => isDict(get(get(c.meta, "columns"), c.enc[k])));
const measuresDistinct = (c: C) => { if (c.enc.y_left === c.enc.y_right) return false; const a = c.vals(c.enc.y_left), b = c.vals(c.enc.y_right); return !(a.length === b.length && a.every((v, i) => v === b[i])); };

const CHECKS: Record<string, (c: C) => boolean> = {
  base_eligible: (c) => c.carriers.some((b) => c.el[b] === true),
  single_row: (c) => c.N === 1, value_present: valuePresent,
  goal_declared: goal, goal_bounds_valid: goalBounds, value_within_bounds: inBounds,
  cat_measure_shape: shapeCat, two_dim_shape: shapeTwo, time_shape: (c) => shapeTime(c, 1), series_shape: series, scatter_shape: scatter, bubble_shape: bubble,
  no_missing_used: noMissing, unique_categories: uniqueDims, unique_pairs: uniqueDims, unique_time: uniqueDims, unique_paths: uniqueDims, category_cap: cap,
  measure_additive: additive, nonnegative: nonneg, groups_disjoint: (c) => c.flag("groups_disjoint"), groups_exhaustive: (c) => c.flag("groups_exhaustive"),
  grid_or_missing_cells_declared: grid, order_declared: wfOrder, total_declared: wfTotal, reconciles,
  slice_range: sliceRange, positive_total: posTotal,
  hierarchy_declared: (c) => hier(c, 1), hierarchy_depth_two: (c) => hier(c, 2), weight_declared: weight,
  weight_additive: (c) => c.colmeta(c.enc.weight).additive === true, weight_positive: (c) => c.vals(c.enc.weight).every((v) => v > 0), leaf_cap: (c) => c.N <= T.treemap_max_leaves,
  raw_samples_declared: rawDeclared, not_precomputed: precomputedOk, sample_column_resolved: sampleCol,
  group_declared: (c) => c.group !== null, groups_min_two: (c) => groups(c).length >= 2,
  group_complete: (c) => !c.group || !c.vals(c.group).some(isMissing), group_cap: (c) => groups(c).length <= MAX_CAT,
  min_samples_histogram: minHist, min_samples_violin: (c) => { const g = groups(c); return g.length > 0 && g.every(([, x]) => x.length >= T.min_samples_violin); },
  min_group_boxplot: minBox, non_constant: nonConst,
  min_rows_line: (c) => c.N >= T.min_rows_line, min_pairs: (c) => c.N >= T.min_pairs_scatter, x_varies: (c) => new Set(c.vals(c.enc.x).map(key)).size > 1,
  size_nonnegative: (c) => c.vals(c.enc.size).every((v) => v >= 0), size_unit_declared: (c) => nonEmptyStr(c.colmeta(c.enc.size).unit),
  dual_measures_declared: dualDeclared, units_declared: (c) => both(c, (m) => nonEmptyStr(m.unit)), axis_labels_declared: (c) => both(c, (m) => nonEmptyStr(m.label)),
  axes_distinct: (c) => c.colmeta(c.enc.y_left).axis === "left" && c.colmeta(c.enc.y_right).axis === "right", measures_distinct: measuresDistinct,
  heatmap_cap: (c) => c.dims.every((n) => new Set(c.vals(n).map(key)).size <= T.heatmap_max_categories),
};

const carriers = (out: string) => Object.entries(SPECIALIZATION).filter(([, o]) => o.includes(out)).map(([b]) => b);
const rank = (scores: unknown): string[] => {
  const base: string[] = [...BASE_CLASSES];
  if (scores === null || scores === undefined) return base;
  const sc: Record<string, any> = Array.isArray(scores) ? Object.fromEntries(BASE_CLASSES.map((b, i) => [b, scores[i]])) : (scores as any);
  const s = (b: string) => (isNum(sc[b]) ? sc[b] : -Infinity);
  return base.map((b, i) => ({b, i})).sort((x, y) => (s(x.b) === s(y.b) ? x.i - y.i : s(y.b) > s(x.b) ? 1 : -1)).map((x) => x.b);
};

/**
 * Choose the concrete output for a result set (SqlVizSpec-Outputs-v1.0.0). `baseEligibility` is required (class -> bool, from rules); a missing class counts as ineligible.
 * Returns {output, encodings, params, rejected, fallback_chain}.
 */
export function specializeOutputs(columns: (string | ColumnSpec)[], rows: Cell[][], metadata?: Record<string, any> | null, baseScores?: Record<string, number> | number[] | null,
  roles?: Record<string, string> | null, baseEligibility?: Record<string, boolean> | null): OutputsResult {
  const cols = resolveColumns(columns, rows), c = new Ctx(cols, rows, metadata, roles, baseEligibility ?? {});
  const rejected: OutputsResult["rejected"] = [], chain: string[] = [], seen = new Set<string>();
  for (const base of rank(baseScores)) {
    for (const out of SPECIALIZATION[base]) {
      if (seen.has(out)) continue;
      seen.add(out); chain.push(out);
      c.reset(); c.output = out; c.carriers = carriers(out);
      let reason: string | null = null;
      for (const p of DEFINITIONS[out].preconditions) {
        const ok = out === "combo_dual_axis" && p.id === "time_shape" ? shapeTime(c, 2) : CHECKS[p.id](c);
        if (!ok) { reason = p.reason; break; }
      }
      if (reason === null) {
        if (out === "table") c.enc = {columns: cols.map((x) => x.name)};
        return {output: out, encodings: {...c.enc}, params: c.params, rejected, fallback_chain: chain};
      }
      rejected.push({output: out, reason_code: reason});
    }
  }
  throw new Error("table is always reachable");
}
