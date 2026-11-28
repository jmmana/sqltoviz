// Measures what the playground ships and how long the experimental WASM engine takes to become usable, per browser.
// Usage: node site/e2e/measure.mjs [runs=5]  (BROWSERS=chromium,firefox,webkit|all; same prerequisites as playground.e2e.mjs). Prints Markdown.
// Cold start = click on "Run experimental model" -> recommendation rendered, in a FRESH browser context (empty cache) against a local static server.
// Warm = a second click in the same page (engine already loaded). Times are wall clock of this machine; localhost transfer, so network latency is excluded.
import http from 'node:http';
import {readFileSync, existsSync, statSync, readdirSync} from 'node:fs';
import {extname, join, normalize} from 'node:path';
import {gzipSync, brotliCompressSync} from 'node:zlib';
import {fileURLToPath} from 'node:url';
import os from 'node:os';
import * as pw from 'playwright';
const root = fileURLToPath(new URL('..', import.meta.url)), runs = Number(process.argv[2] ?? 5);
const types = {'.html': 'text/html', '.mjs': 'text/javascript', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.wasm': 'application/wasm'};
const server = http.createServer((req, res) => {
  const p = decodeURIComponent(new URL(req.url, 'http://x').pathname), f = normalize(join(root, p === '/' ? 'index.html' : p));
  if (!f.startsWith(root) || !existsSync(f) || !statSync(f).isFile()) { res.writeHead(404).end(); return; }
  res.writeHead(200, {'content-type': types[extname(f)] ?? 'application/octet-stream'}).end(readFileSync(f));
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const base = 'http://127.0.0.1:' + server.address().port + '/';
const med = (a) => { const s = [...a].sort((x, y) => x - y), i = s.length >> 1; return s.length % 2 ? s[i] : (s[i - 1] + s[i]) / 2; };
const kb = (n) => (n / 1024).toFixed(1) + ' KiB', mb = (n) => (n / 1048576).toFixed(2) + ' MiB';
// Static payload, from the bytes actually served (raw / gzip -9 / brotli q11 are what a CDN could send; GitHub Pages serves gzip).
const walk = (d) => readdirSync(d, {withFileTypes: true}).flatMap((e) => e.isDirectory() ? walk(join(d, e.name)) : [join(d, e.name)]);
const group = (label, files) => { const bufs = files.map((f) => readFileSync(f)); return {label, n: files.length, raw: bufs.reduce((s, b) => s + b.length, 0), gz: bufs.reduce((s, b) => s + gzipSync(b, {level: 9}).length, 0), br: bufs.reduce((s, b) => s + brotliCompressSync(b).length, 0)}; };
const under = (d) => walk(join(root, d));
const groups = [
  group('onnxruntime-web WASM binary', [join(root, 'vendor/ort/ort-wasm-simd-threaded.wasm')]),
  group('onnxruntime-web JS (2 files)', ['vendor/ort/ort.wasm.min.mjs', 'vendor/ort/ort-wasm-simd-threaded.mjs'].map((f) => join(root, f))),
  group('ONNX candidate models + manifest', under('models')),
  group('SDK modules (site/sdk)', under('sdk')),
  group('Playground code (html/css/mjs, excl. generated)', ['index.html', 'style.css', ...readdirSync(root).filter((f) => f.endsWith('.mjs') && !f.endsWith('.test.mjs'))].map((f) => join(root, f))),
];
console.log(`## Playground payload (served bytes)\n\n| Part | Files | Raw | gzip -9 | brotli q11 |\n|---|---|---|---|---|`);
for (const g of groups) console.log(`| ${g.label} | ${g.n} | ${kb(g.raw)} | ${kb(g.gz)} | ${kb(g.br)} |`);
const sum = (k) => groups.slice(0, 4).reduce((s, g) => s + g[k], 0);
console.log(`| Engine total (rows 1-4, loaded only on "Run experimental model") | | ${mb(sum('raw'))} | ${mb(sum('gz'))} | ${mb(sum('br'))} |\n`);
const wanted = (process.env.BROWSERS ?? 'chromium') === 'all' ? ['chromium', 'firefox', 'webkit'] : (process.env.BROWSERS ?? 'chromium').split(',');
console.log(`## Cold start of the WASM engine (${runs} fresh contexts per browser; median / min / max ms)\n\n| Browser | version | Playground ready (load event) | Cold: click -> result | Warm: click -> result | Bytes fetched on cold click |\n|---|---|---|---|---|---|`);
try {
  for (const name of wanted) {
    const browser = await pw[name].launch(), load = [], cold = [], warm = []; let bytes = 0;
    try {
      for (let i = 0; i < runs; i++) {
        const ctx = await browser.newContext(), page = await ctx.newPage(); let got = 0, count = false;
        page.on('response', async (r) => { if (count) { try { got += (await r.body()).length; } catch {} } });
        const t0 = Date.now(); await page.goto(base, {waitUntil: 'load'}); load.push(Date.now() - t0);
        const shot = async () => { const t = Date.now(); await page.click('#run-model'); await page.waitForFunction(() => /Model status/.test(document.getElementById('model-out').innerText) && !document.getElementById('run-model').disabled, null, {timeout: 120000}); return Date.now() - t; };
        count = true; cold.push(await shot()); count = false; bytes = got;
        warm.push(await shot()); await ctx.close();
      }
      const f = (a) => `${Math.round(med(a))} / ${Math.min(...a)} / ${Math.max(...a)}`;
      console.log(`| ${name} | ${browser.version()} | ${f(load)} | ${f(cold)} | ${f(warm)} | ${mb(bytes)} |`);
    } finally { await browser.close(); }
  }
} finally { server.close(); }
console.log(`\nMachine: ${os.cpus()[0].model}, ${os.platform()} ${os.release()}, Node ${process.version}, Playwright ${JSON.parse(readFileSync(join(root, '..', 'node_modules/playwright/package.json'), 'utf8')).version}. Single run of this script; not a benchmark of other hardware or real networks.`);
