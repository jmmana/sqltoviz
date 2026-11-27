// Experimental ONNX engine for the playground: runs entirely in the browser (WASM, single thread). No data leaves the page.
// Requires the generated site/sdk, site/models and site/vendor/ort (node site/build-engine.mjs). Models are CANDIDATES, not scientifically validated.
let pending;
export async function loadEngine(base = import.meta.url, deps = {}) {
  pending ??= (async () => {
    const at = (p) => new URL(p, base).href;
    const [{Engine}, {createWebRunner}] = await Promise.all([import('./sdk/engine.js'), import('./sdk/web.js')]);
    const ort = deps.ort ?? await import('./vendor/ort/ort.wasm.min.mjs');
    ort.env.wasm.wasmPaths = at('./vendor/ort/');
    const fetchJson = deps.fetchJson ?? (async (u) => (await fetch(u)).json());
    const manifest = await fetchJson(at('./models/manifest.json'));
    const chart = await createWebRunner(at('./models/' + manifest.chart.file), manifest.chart.sha256, 'chart', {ort, fetch: deps.fetch});
    const role = await createWebRunner(at('./models/' + manifest.role.file), manifest.role.sha256, 'role', {ort, fetch: deps.fetch});
    return new Engine({chart, role, chartStatus: manifest.chart.status});
  })();
  try { return await pending; } catch (e) { pending = undefined; throw e; }
}
/** rows: array of row objects (as in the JSON editor). Returns the engine recommendation. */
export async function analyze(engine, sql, rows) {
  if (!Array.isArray(rows) || rows.length < 1 || rows.some((r) => !r || typeof r !== 'object' || Array.isArray(r))) throw new Error('Provide 1+ JSON objects.');
  const keys = Object.keys(rows[0]);
  return engine.recommend(sql, keys.map((name) => ({name})), rows.map((r) => keys.map((k) => (k in r ? r[k] : null))));
}
