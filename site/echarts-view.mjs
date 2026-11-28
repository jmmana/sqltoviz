// Optional ECharts renderer for the playground, driven by the SDK adapter toEcharts(). ECharts is vendored under site/vendor/echarts (same origin, no CDN).
// Supported by the adapter: bar, horizontal_bar, line. Other recommendations keep the built-in SVG/table rendering.
import {toEcharts} from './sdk/index.js';
import {computeInsights, describeInsights, outlierIndexes} from './insights.mjs';
let loading;
export function loadEcharts(src = new URL('./vendor/echarts/echarts.min.js', import.meta.url).href) {
  if (globalThis.echarts) return Promise.resolve(globalThis.echarts);
  loading ??= new Promise((ok, fail) => { const s = document.createElement('script'); s.src = src; s.onload = () => ok(globalThis.echarts); s.onerror = () => { loading = undefined; fail(new Error('ECharts bundle not found (run node site/build-engine.mjs)')); }; document.head.append(s); });
  return loading;
}
export const echartsSupported = (plan) => ['bar', 'horizontal_bar', 'line'].includes(plan.chartType);
/** Adapter option + MAD outlier highlighting (orange points/bars) taken from the same detector the insights panel uses. */
export function buildOption(plan, rows, insights) {
  const option = toEcharts(plan, rows), hit = new Set(outlierIndexes(insights, plan.encodings.y)), cs = getComputedStyle(document.body), fg = cs.color;
  option.series[0].data = option.series[0].data.map((value, i) => hit.has(i) ? {value, itemStyle: {color: '#f97316'}} : value);
  option.tooltip = {trigger: 'axis'}; option.grid = {containLabel: true, left: 12, right: 24, top: 36, bottom: 12};
  option.textStyle = {color: fg}; option.animation = false;
  for (const a of [option.xAxis, option.yAxis]) { a.nameTextStyle = {color: fg}; a.axisLabel = {color: fg}; a.axisLine = {lineStyle: {color: fg}}; }
  option.aria = {enabled: true};
  return option;
}
export function initializeViz({host, renderer, insightsRoot, getLang, onNote}) {
  let chart, last, additive = false;
  const lang = () => getLang(), el = (tag, text) => { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; return e; };
  const renderInsights = () => {
    if (!last) { insightsRoot.replaceChildren(); return; }
    const d = describeInsights(computeInsights(last.plan, last.rows, {additive}), lang()), box = el('div'), label = el('label'), cb = el('input');
    cb.type = 'checkbox'; cb.checked = additive; cb.onchange = () => { additive = cb.checked; renderInsights(); };
    label.className = 'additive'; label.append(cb, ' ' + d.additiveLabel);
    box.append(el('h4', d.title), el('p', d.note));
    for (const s of d.sections) { const sec = el('section'); sec.dataset.insight = s.id; const ul = el('ul'); s.lines.forEach((l) => ul.append(el('li', l))); sec.append(el('h5', s.heading), ul); if (s.id === 'pareto') sec.append(label); box.append(sec); }
    insightsRoot.replaceChildren(box);
  };
  const draw = async () => {
    const native = host.nextElementSibling; // #chart (built-in renderer)
    if (!last) return;
    const want = renderer.value === 'echarts' && echartsSupported(last.plan);
    host.hidden = !want; native.hidden = want; onNote(renderer.value === 'echarts' && !want ? (lang() === 'es' ? 'ECharts no cubre este tipo de gráfico; se usa el render integrado.' : 'ECharts does not cover this chart type; using the built-in renderer.') : '');
    if (!want) { chart?.dispose(); chart = undefined; return; }
    try {
      const ec = await loadEcharts();
      if (host.hidden) return;
      chart ??= ec.init(host, null, {renderer: 'svg'});
      chart.setOption(buildOption(last.plan, last.rows, computeInsights(last.plan, last.rows, {additive})), true); chart.resize();
      host.dataset.rendered = last.plan.chartType;
    } catch (e) { host.hidden = true; native.hidden = false; onNote(e.message); }
  };
  renderer.onchange = draw;
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(() => chart?.resize()).observe(host);
  return {update(plan, rows) { last = {plan, rows}; renderInsights(); return draw(); }, clear() { last = undefined; insightsRoot.replaceChildren(); host.hidden = true; host.nextElementSibling.hidden = false; chart?.dispose(); chart = undefined; }, refresh() { renderInsights(); return draw(); }};
}
