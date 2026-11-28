// Statistical insights for the playground. Every number comes from the SDK detectors (madOutliers, temporalShifts, pareto, pearson);
// each result keeps its explicit status (ok, zero_mad, insufficient_samples, unknown_additivity, ...) and nothing is estimated here.
import {madOutliers, temporalShifts, pareto, pearson} from './sdk/index.js';
const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
export function numericColumns(rows) {
  const keys = Object.keys(rows[0] ?? {});
  return keys.filter((k) => rows.some((r) => isNum(r[k])) && rows.every((r) => r[k] === null || isNum(r[k])));
}
/** plan: {chartType, encodings}; opts.additive: user-confirmed additivity for Pareto (default false => unknown_additivity). */
export function computeInsights(plan, rows, opts = {}) {
  const cols = numericColumns(rows), column = (k) => rows.map((r) => r[k]);
  const out = {columns: cols.map((name) => ({name, mad: madOutliers(column(name))})), shifts: null, pareto: null, correlations: []};
  const {x, y} = plan.encodings ?? {};
  if (plan.chartType === 'line' && y) out.shifts = {column: y, items: temporalShifts(column(y)), labels: x ? column(x).map(String) : []};
  if ((plan.chartType === 'bar' || plan.chartType === 'horizontal_bar') && y) {
    const r = pareto(column(y), 0.8, opts.additive === true);
    out.pareto = {column: y, status: r.status, coverage: 0.8, items: r.items, labels: x ? column(x).map(String) : []};
  }
  const use = cols.slice(0, 4);
  for (let i = 0; i < use.length; i++) for (let j = i + 1; j < use.length; j++) out.correlations.push({x: use[i], y: use[j], ...pearson(column(use[i]), column(use[j]))});
  return out;
}
/** Indexes flagged by the MAD detector for a column (empty unless status is ok). */
export function outlierIndexes(insights, column) {
  const c = insights.columns.find((k) => k.name === column);
  return c && c.mad.status === 'ok' ? c.mad.outliers.map((o) => o.index) : [];
}
const STATUS = {
  en: {ok: 'ok', zero_mad: 'zero MAD: more than half of the values are identical, outliers cannot be scored', insufficient_samples: 'insufficient samples (need at least 3 numeric values)', numeric_overflow: 'numeric overflow', unknown_additivity: 'unknown additivity: confirm the values are additive to compute Pareto shares', invalid_weights: 'invalid weights (negative or non-numeric)', zero_total: 'zero total', constant_column: 'constant column: correlation undefined', missing: 'missing value', zero_baseline: 'zero baseline: relative change undefined', none: 'fewer than two numeric columns: no correlation to compute'},
  es: {ok: 'ok', zero_mad: 'MAD cero: más de la mitad de los valores son idénticos, no se pueden puntuar atípicos', insufficient_samples: 'muestras insuficientes (se necesitan al menos 3 valores numéricos)', numeric_overflow: 'desbordamiento numérico', unknown_additivity: 'aditividad desconocida: confirma que los valores son aditivos para calcular Pareto', invalid_weights: 'pesos inválidos (negativos o no numéricos)', zero_total: 'total cero', constant_column: 'columna constante: correlación indefinida', missing: 'valor ausente', zero_baseline: 'base cero: cambio relativo indefinido', none: 'menos de dos columnas numéricas: no hay correlación que calcular'},
};
export const statusText = (status, lang = 'en') => (STATUS[lang] ?? STATUS.en)[status] ?? status;
const T = {
  en: {title: 'Statistical insights', note: 'Computed locally by the SDK detectors; statuses are shown instead of guessing.', mad: 'Outliers (MAD, threshold 3.5)', shifts: 'Largest period-over-period changes', pareto: 'Pareto (80% coverage)', corr: 'Pearson correlation', outliers: 'outliers', none: 'none', additive: 'Values are additive (I confirm)', status: 'status', median: 'median'},
  es: {title: 'Hallazgos estadísticos', note: 'Calculados localmente por los detectores del SDK; se muestran los estados en lugar de adivinar.', mad: 'Atípicos (MAD, umbral 3.5)', shifts: 'Mayores cambios entre periodos', pareto: 'Pareto (80 % de cobertura)', corr: 'Correlación de Pearson', outliers: 'atípicos', none: 'ninguno', additive: 'Los valores son aditivos (lo confirmo)', status: 'estado', median: 'mediana'},
};
const pct = (v) => (v * 100).toFixed(1) + '%';
/** Returns plain {title, note, sections:[{heading, lines:[string]}]} so it can be tested without a DOM. */
export function describeInsights(ins, lang = 'en') {
  const t = T[lang] ?? T.en, st = (s) => statusText(s, lang), sections = [];
  sections.push({id: 'mad', heading: t.mad, lines: ins.columns.length ? ins.columns.map((c) => {
    const m = c.mad;
    return m.status === 'ok' ? `${c.name}: ${m.outliers.length ? m.outliers.map((o) => `#${o.index + 1} (${o.score.toFixed(2)})`).join(', ') : t.none} · ${t.median} ${m.median}` : `${c.name}: ${t.status} ${m.status} (${st(m.status)})`;
  }) : ['-']});
  if (ins.shifts) {
    const ok = ins.shifts.items.filter((s) => s.status === 'ok' && s.relative_change !== null).sort((a, b) => Math.abs(b.relative_change) - Math.abs(a.relative_change)).slice(0, 3);
    const bad = ins.shifts.items.filter((s) => s.status !== 'ok');
    sections.push({id: 'shifts', heading: `${t.shifts}: ${ins.shifts.column}`, lines: [...ok.map((s) => `${ins.shifts.labels[s.index - 1] ?? s.index} → ${ins.shifts.labels[s.index] ?? s.index + 1}: ${s.delta >= 0 ? '+' : ''}${s.delta} (${s.relative_change >= 0 ? '+' : ''}${pct(s.relative_change)})`), ...bad.slice(0, 3).map((s) => `#${s.index + 1}: ${t.status} ${s.status} (${st(s.status)})`)]});
  }
  if (ins.pareto) {
    const p = ins.pareto, lines = [];
    if (p.status !== 'ok') lines.push(`${t.status} ${p.status} (${st(p.status)})`);
    else { const inc = p.items.filter((i) => i.included); lines.push(`${inc.length}/${p.items.length}: ${inc.map((i) => `${p.labels[i.index] ?? i.index} ${pct(i.share)}`).join(', ')} → ${pct(inc[inc.length - 1]?.cumulative ?? 0)}`); }
    sections.push({id: 'pareto', heading: `${t.pareto}: ${p.column}`, lines});
  }
  sections.push({id: 'corr', heading: t.corr, lines: ins.correlations.length ? ins.correlations.map((c) => c.status === 'ok' ? `${c.x} ~ ${c.y}: r = ${c.r.toFixed(3)} (n = ${c.n})` : `${c.x} ~ ${c.y}: ${t.status} ${c.status} (${st(c.status)})`) : [st('none')]});
  return {title: t.title, note: t.note, additiveLabel: t.additive, sections};
}
