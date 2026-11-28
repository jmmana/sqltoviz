// SDK benchmark (Node). Same JSON schema/scenarios as bench_python.py. Usage: node benchmarks/bench_node.mjs OUT.json [reps]  |  internal: --child N
import {writeFileSync} from 'node:fs';
import {performance} from 'node:perf_hooks';
import {execFileSync} from 'node:child_process';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';
const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..', 'packages', 'npm');
const SQL = 'SELECT category, region, SUM(value) AS value, day FROM t GROUP BY category, region, day ORDER BY day';
const SCHEMA = [{name: 'category'}, {name: 'region'}, {name: 'value'}, {name: 'day'}];
const SIZES = [10, 100, 1000, 10000];
const rowsFor = (n) => Array.from({length: n}, (_, i) => [`cat${(i * 7) % 12}`, `reg${(i * 3) % 5}`, ((i * 37) % 1000) + ((i * 13) % 100) / 100, `2024-${String(1 + i % 12).padStart(2, '0')}-${String(1 + i % 27).padStart(2, '0')}`]);
const pct = (a, q) => { a = [...a].sort((x, y) => x - y); const k = (a.length - 1) * q / 100, lo = Math.floor(k); return (a[lo] + (a[Math.min(lo + 1, a.length - 1)] - a[lo]) * (k - lo)); };
const sdk = await import(join(root, 'dist/esm/index.js'));
const node = await import(join(root, 'dist/esm/node.js'));
const {readFile} = await import('node:fs/promises');
async function runners() {
  const dir = node.bundledModelsDir(), man = JSON.parse(await readFile(join(dir, 'manifest.json'), 'utf8'));
  return {chart: await node.createNodeRunner(join(dir, man.chart.file), man.chart.sha256, 'chart'), role: await node.createNodeRunner(join(dir, man.role.file), man.role.sha256, 'role')};
}
async function one(chart, rows) {
  const t0 = performance.now(); const {table, columns} = sdk.extractFeatures(SQL, SCHEMA, rows); const t1 = performance.now();
  const s = await chart.run(table, 1, 32); const t2 = performance.now();
  sdk.constrainedChoice(s, table, columns); const t3 = performance.now();
  return [t1 - t0, t2 - t1, t3 - t2];
}
if (process.argv[2] === '--child') {
  const n = Number(process.argv[3]); const {chart} = await runners(); const rows = rowsFor(n); await one(chart, rows);
  const b = process.resourceUsage().maxRSS * 1024; for (let i = 0; i < 30; i++) await one(chart, rows);
  console.log(JSON.stringify({baseline: b, peak: process.resourceUsage().maxRSS * 1024})); process.exit(0);
}
const out = process.argv[2], reps = Number(process.argv[3] ?? 400);
let t0 = performance.now(); const r = await runners(); const loadMs = performance.now() - t0;
const cpu = os.cpus()[0]?.model ?? os.arch();
const res = {sdk: 'typescript-node', environment: {cpu, os: `${os.type()} ${os.release()}`, runtime: `Node ${process.version}`, onnxruntime: 'onnxruntime-node', threads: 1},
  load: {import_ms: 0, engine_load_ms: loadMs, note: 'createNodeRunner x2 (chart+role): checksum + sessions (cold, first call)'}, sizes: {}};
for (const n of SIZES) {
  const rows = rowsFor(n), k = n <= 1000 ? reps : Math.max(Math.floor(reps / 8), 40);
  for (let i = 0; i < 20; i++) await one(r.chart, rows);
  const ex = [], inf = [], con = [], tot = [];
  for (let i = 0; i < k; i++) { const [a, b, c] = await one(r.chart, rows); ex.push(a); inf.push(b); con.push(c); tot.push(a + b + c); }
  const m = JSON.parse(execFileSync(process.execPath, [fileURLToPath(import.meta.url), '--child', String(n)], {encoding: 'utf8'}));
  res.sizes[n] = {runs: k, extract_ms: {median: pct(ex, 50), p95: pct(ex, 95), p99: pct(ex, 99)}, onnx_ms: {median: pct(inf, 50), p95: pct(inf, 95)},
    constraints_ms: {median: pct(con, 50), p95: pct(con, 95)}, end_to_end_ms: {median: pct(tot, 50), p95: pct(tot, 95), p99: pct(tot, 99)},
    peak_rss_mb: m.peak / 1e6, rss_growth_mb: (m.peak - m.baseline) / 1e6};
}
writeFileSync(out, JSON.stringify(res, null, 1));
console.log(JSON.stringify(Object.fromEntries(Object.entries(res.sizes).map(([n, d]) => [n, +d.end_to_end_ms.median.toFixed(3)]))), 'load_ms', loadMs.toFixed(1));
