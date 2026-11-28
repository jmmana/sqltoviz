// Real-browser test (Chromium via Playwright): the experimental ONNX model runs in WASM inside the page, labelled experimental, with NO external requests.
// Usage: node site/e2e/playground.e2e.mjs   (requires: node site/build-engine.mjs; npm i --no-save playwright@1.65.1; npx playwright install chromium)
import http from 'node:http';
import {readFileSync, existsSync, statSync} from 'node:fs';
import {extname, join, normalize} from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
const root = fileURLToPath(new URL('..', import.meta.url));
const assets = fileURLToPath(new URL('../../docs/assets', import.meta.url));
const types = {'.html': 'text/html', '.mjs': 'text/javascript', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.wasm': 'application/wasm', '.onnx': 'application/octet-stream', '.svg': 'image/svg+xml'};
const server = http.createServer((req, res) => {
  const p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  let f = normalize(join(p.startsWith('/assets/') ? assets : root, p.startsWith('/assets/') ? p.slice(8) : p === '/' ? 'index.html' : p));
  if (!existsSync(f) || !statSync(f).isFile()) { res.writeHead(404).end(); return; }
  res.writeHead(200, {'content-type': types[extname(f)] ?? 'application/octet-stream'}).end(readFileSync(f));
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const base = 'http://127.0.0.1:' + server.address().port + '/';
const browser = await chromium.launch();
try {
  const page = await browser.newPage(), external = [], errors = [];
  page.on('request', (r) => { if (!r.url().startsWith(base) && !r.url().startsWith('data:') && !r.url().startsWith('blob:')) external.push(r.url()); });
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(base);
  await page.fill('#sql', 'SELECT 1 AS value');
  await page.fill('#rows', '[{"value":1}]');
  await page.click('#format-rows');
  assert.equal(await page.inputValue('#rows'), JSON.stringify([{value: 1}], null, 2));
  await page.locator('#rows').press('Control+Enter');
  assert.equal(await page.innerText('#result'), 'kpi');
  await page.fill('#rows', '[');
  await page.click('#format-rows');
  assert.equal(await page.inputValue('#rows'), '[');
  assert.match(await page.innerText('#editor-status'), /Check its syntax/);
  await page.click('#load');
  await page.click('#run-model');
  await page.waitForFunction(() => /Model status/.test(document.getElementById('model-out').innerText), null, {timeout: 120000});
  const out = await page.innerText('#model-out');
  assert.match(out, /Chart \(after constraints\): \w+/);
  assert.match(out, /Model status: experimental/);
  assert.match(out, /not scientifically validated/);
  assert.match(out, /Roles: /);
  await page.locator('#model-out summary').click();
  const tensors = JSON.parse(await page.locator('#model-out pre').innerText());
  assert.match(tensors.contract_version, /^SqlVizSpec-v/);
  assert.equal(tensors.model_status, 'experimental');
  assert.deepEqual(tensors.table.shape, [1, 32]);
  assert.deepEqual(tensors.columns.shape, [2, 28]);
  assert.deepEqual(tensors.columns.names, ['category', 'value']);
  assert.equal(tensors.table.values[0].length, 32);
  assert.equal(tensors.columns.values[0].length, 28);
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', {name: 'Download tensor JSON'}).click();
  const download = await downloadPromise;
  assert.equal(download.suggestedFilename(), 'sqltoviz-tensors.json');
  assert.deepEqual(JSON.parse(readFileSync(await download.path(), 'utf8')), tensors);
  assert.deepEqual(external, [], 'the playground must not contact external hosts');
  assert.deepEqual(errors, []);
  console.log('playground e2e ok:', out.split('\n')[0]);
} finally { await browser.close(); server.close(); }
