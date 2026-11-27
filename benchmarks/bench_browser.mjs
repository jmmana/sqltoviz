// Browser (Chromium, WASM single thread) benchmark with the same scenarios/JSON schema as the other SDKs.
// Usage: node benchmarks/bench_browser.mjs OUT.json [reps]   (needs: node site/build-engine.mjs; npm i --no-save playwright; npx playwright install chromium)
import http from 'node:http';
import {readFileSync, existsSync, statSync, writeFileSync} from 'node:fs';
import {extname, join, normalize} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';
const site = fileURLToPath(new URL('../site', import.meta.url));
const types = {'.html': 'text/html', '.mjs': 'text/javascript', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.wasm': 'application/wasm'};
const server = http.createServer((req, res) => {
  const p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  const f = normalize(join(site, p === '/' ? 'index.html' : p));
  if (!f.startsWith(site) || !existsSync(f) || !statSync(f).isFile()) { res.writeHead(404).end(); return; }
  res.writeHead(200, {'content-type': types[extname(f)] ?? 'application/octet-stream'}).end(readFileSync(f));
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const base = 'http://127.0.0.1:' + server.address().port + '/';
const reps = Number(process.argv[3] ?? 400);
const browser = await chromium.launch();
try {
  const page = await browser.newPage(); await page.goto(base);
  const out = await page.evaluate(async ({reps}) => {
    const SQL = 'SELECT category, region, SUM(value) AS value, day FROM t GROUP BY category, region, day ORDER BY day';
    const SCHEMA = [{name: 'category'}, {name: 'region'}, {name: 'value'}, {name: 'day'}];
    const rowsFor = (n) => Array.from({length: n}, (_, i) => [`cat${(i * 7) % 12}`, `reg${(i * 3) % 5}`, ((i * 37) % 1000) + ((i * 13) % 100) / 100, `2024-${String(1 + i % 12).padStart(2, '0')}-${String(1 + i % 27).padStart(2, '0')}`]);
    const pct = (a, q) => { a = [...a].sort((x, y) => x - y); const k = (a.length - 1) * q / 100, lo = Math.floor(k); return a[lo] + (a[Math.min(lo + 1, a.length - 1)] - a[lo]) * (k - lo); };
    const t0 = performance.now();
    const sdk = await import('./sdk/index.js'), web = await import('./sdk/web.js'), ort = await import('./vendor/ort/ort.wasm.min.mjs');
    ort.env.wasm.wasmPaths = new URL('./vendor/ort/', location.href).href;
    const man = await (await fetch('./models/manifest.json')).json();
    const chart = await web.createWebRunner('./models/' + man.chart.file, man.chart.sha256, 'chart', {ort});
    const role = await web.createWebRunner('./models/' + man.role.file, man.role.sha256, 'role', {ort});
    const loadMs = performance.now() - t0;
    // performance.now() is coarsened to 0.1 ms in non-isolated pages: time batches of B calls per phase and report per-call means (median/p95 over batches)
    const batch = async (rows, B) => {
      let table, columns, s; const a = performance.now();
      for (let i = 0; i < B; i++) ({table, columns} = sdk.extractFeatures(SQL, SCHEMA, rows));
      const b = performance.now();
      for (let i = 0; i < B; i++) s = await chart.run(table, 1, 32);
      const c = performance.now();
      for (let i = 0; i < B; i++) sdk.constrainedChoice(s, table, columns);
      const d = performance.now();
      return [(b - a) / B, (c - b) / B, (d - c) / B];
    };
    const sizes = {};
    for (const n of [10, 100, 1000, 10000]) {
      const rows = rowsFor(n), B = n <= 100 ? 50 : n === 1000 ? 10 : 1, k = n <= 1000 ? Math.max(Math.floor(reps / 8), 40) : 40;
      for (let i = 0; i < 4; i++) await batch(rows, B);
      const ex = [], inf = [], con = [], tot = [];
      for (let i = 0; i < k; i++) { const [x, y, z] = await batch(rows, B); ex.push(x); inf.push(y); con.push(z); tot.push(x + y + z); }
      sizes[n] = {runs: k * B, batch_size: B, extract_ms: {median: pct(ex, 50), p95: pct(ex, 95), p99: pct(ex, 99)}, onnx_ms: {median: pct(inf, 50), p95: pct(inf, 95)}, constraints_ms: {median: pct(con, 50), p95: pct(con, 95)}, end_to_end_ms: {median: pct(tot, 50), p95: pct(tot, 95), p99: pct(tot, 99)}};
    }
    return {loadMs, sizes, ua: navigator.userAgent, heap: performance.memory ? performance.memory.usedJSHeapSize / 1e6 : null};
  }, {reps});
  const res = {sdk: 'typescript-browser-wasm', environment: {cpu: 'same machine', os: process.platform, runtime: out.ua, onnxruntime: 'onnxruntime-web (WASM, 1 thread)', threads: 1},
    load: {import_ms: 0, engine_load_ms: out.loadMs, note: 'dynamic import of SDK + ORT-web, fetch + checksum + 2 WASM sessions (cold, same-origin localhost, no network latency)'}, sizes: out.sizes, js_heap_mb: out.heap, note: 'per-call means over batches (timer resolution 0.1 ms in non-isolated pages); p95 is over batch means'};
  writeFileSync(process.argv[2], JSON.stringify(res, null, 1));
  console.log(JSON.stringify(Object.fromEntries(Object.entries(out.sizes).map(([n, d]) => [n, +d.end_to_end_ms.median.toFixed(3)]))), 'load_ms', out.loadMs.toFixed(0));
} finally { await browser.close(); server.close(); }
