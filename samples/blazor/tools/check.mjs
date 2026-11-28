// Usage: node check.mjs wasm <dir-with-published-wwwroot> | node check.mjs server <dll-dir>
// Starts the published sample, loads it in headless Chromium (WASM) or fetches it (Server) and asserts the report.
import { spawn } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
const [mode, dir] = process.argv.slice(2);
const fail = (m) => { console.error('FAIL: ' + m); process.exit(1); };
const MIME = { '.wasm': 'application/wasm', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.html': 'text/html', '.dat': 'application/octet-stream', '.onnx': 'application/octet-stream' };
function serve(root, port) {
  return new Promise((res) => { const s = http.createServer((q, r) => {
    let p = path.join(root, decodeURIComponent(q.url.split('?')[0])); if (p.endsWith(path.sep)) p += 'index.html';
    if (!fs.existsSync(p) || fs.statSync(p).isDirectory()) p = path.join(root, 'index.html');
    r.writeHead(200, { 'content-type': MIME[path.extname(p)] ?? 'application/octet-stream' }); fs.createReadStream(p).pipe(r); }).listen(port, () => res(s)); });
}
const expected = ['final=kpi', 'final=donut', 'final=table'];
if (mode === 'wasm') {
  const { chromium } = await import('playwright');
  const s = await serve(dir, 18900); const b = await chromium.launch(); const page = await b.newPage();
  const t = Date.now(); await page.goto('http://localhost:18900/');
  await page.waitForFunction(() => document.querySelector('#report')?.textContent.includes('DONE'), null, { timeout: 120000 });
  const report = await page.locator('#report').textContent(); console.log(report, `\nwall_ms=${Date.now() - t}`);
  if (process.argv[4] === 'ort') for (const e of expected) if (!report.includes('ORTWEB ' + e)) fail('missing ORTWEB ' + e);
  if (!report.includes('RULES_ONLY ok')) fail('rules-only failed');
  await b.close(); s.close();
} else if (mode === 'server') {
  const p = spawn('dotnet', ['Server.dll'], { cwd: dir, env: { ...process.env, ASPNETCORE_URLS: 'http://localhost:18901' }, stdio: 'inherit' });
  let html = ''; for (let i = 0; i < 40 && !html.includes('DONE'); i++) { await new Promise(r => setTimeout(r, 500)); html = await fetch('http://localhost:18901/').then(r => r.text()).catch(() => ''); }
  p.kill(); console.log(html.match(/<pre id="report">[\s\S]*?<\/pre>/)?.[0] ?? html.slice(0, 500));
  for (const e of expected) if (!html.includes('NATIVE ' + e)) fail('missing NATIVE ' + e);
  if (!html.includes('ONNX ok')) fail('ONNX load failed');
} else fail('mode');
