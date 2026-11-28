// Real-browser test (Chromium via Playwright): the experimental ONNX model runs in WASM inside the page, labelled experimental, with NO external requests.
// Usage: node site/e2e/playground.e2e.mjs   (requires: node site/build-engine.mjs; npm i --no-save playwright@1.65.1; npx playwright install chromium [firefox webkit])
// Browsers: BROWSERS=chromium,firefox,webkit (default chromium; 'all' = the three). Each one runs the same assertions; a browser that is not installed fails loudly.
import http from 'node:http';
import {readFileSync, existsSync, statSync} from 'node:fs';
import {extname, join, normalize} from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import * as pw from 'playwright';
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
const wanted = (process.env.BROWSERS ?? 'chromium') === 'all' ? ['chromium', 'firefox', 'webkit'] : (process.env.BROWSERS ?? 'chromium').split(',');
async function check(name) {
  const browser = await pw[name].launch();
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
    // ECharts renderer + statistical insights (issue #75)
    await page.selectOption('#example', 'bar'); await page.click('#load');
    await page.fill('#rows', JSON.stringify([10, 11, 10, 12, 11, 500].map((value, i) => ({category: 'c' + i, value}))));
    await page.click('#run');
    assert.match(await page.innerText('#insights [data-insight=mad]'), /#6/, 'MAD flags the 500 outlier');
    assert.match(await page.innerText('#insights [data-insight=pareto]'), /unknown_additivity/);
    assert.match(await page.innerText('#insights [data-insight=corr]'), /fewer than two numeric columns/);
    await page.selectOption('#renderer', 'echarts');
    await page.waitForSelector('#echart[data-rendered=bar] svg', {timeout: 20000});
    assert.equal(await page.locator('#chart').isHidden(), true);
    assert.ok((await page.locator('#echart svg').first().boundingBox()).width > 100, 'ECharts SVG has a layout');
    assert.ok(await page.locator('#echart svg path[fill="#f97316"]').count() >= 1, 'outlier bar highlighted');
    await page.check('#insights input[type=checkbox]');
    assert.match(await page.innerText('#insights [data-insight=pareto]'), /\d+\/6/);
    await page.fill('#rows', '[{"value":1}]'); await page.click('#run');
    assert.equal(await page.locator('#chart').isVisible(), true, 'kpi falls back to the built-in renderer');
    assert.match(await page.innerText('#renderer-note'), /does not cover/);
    await page.click('#lang');
    assert.match(await page.innerText('#insights'), /Hallazgos estadísticos/);
    await page.click('#lang');
    await page.selectOption('#renderer', 'svg');
    assert.deepEqual(external, [], 'the playground must not contact external hosts');
    assert.deepEqual(errors, []);
    console.log(`playground e2e ok [${name}]:`, out.split('\n')[0]);
  } finally { await browser.close(); }
}
try { for (const name of wanted) await check(name); } finally { server.close(); }
