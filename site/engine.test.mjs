import {test} from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const here = fileURLToPath(new URL('.', import.meta.url));
const built = existsSync(here + 'sdk/engine.js') && existsSync(here + 'models/manifest.json');
const skip = built ? false : 'run node site/build-engine.mjs first';
test('playground engine: analyze() with the bundled experimental models over the WASM runtime', {skip}, async () => {
  const ort = await import(createRequire(import.meta.url).resolve('../packages/npm/node_modules/onnxruntime-web/dist/ort.node.min.mjs'));
  const {loadEngine, analyze} = await import('./engine.mjs');
  const fetchBytes = async (u) => { const b = readFileSync(fileURLToPath(u)); return {arrayBuffer: async () => b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength)}; };
  const engine = await loadEngine(new URL('./', import.meta.url).href, {ort, fetch: fetchBytes, fetchJson: async (u) => JSON.parse(readFileSync(fileURLToPath(u), 'utf8'))});
  const rows = [{dept: 'a', total: 10}, {dept: 'b', total: 20}, {dept: 'c', total: 5}];
  const r = await analyze(engine, 'SELECT dept, SUM(sal) AS total FROM emp GROUP BY dept', rows);
  assert.equal(r.model_status, 'experimental');
  assert.ok(r.warnings.some((w) => /not scientifically validated/.test(w)));
  assert.equal(r.roles.length, 2);
  assert.ok(Math.abs(Object.values(r.scores).reduce((a, b) => a + b, 0) - 1) < 1e-5);
  const k = await analyze(engine, 'SELECT SUM(x) AS s FROM t', [{s: 3}]);
  assert.equal(k.final_class, 'kpi');
  await assert.rejects(analyze(engine, 'SELECT 1', []), /JSON objects/);
});
test('generated engine files are not committed', () => {
  const ignore = readFileSync(here + '../.gitignore', 'utf8');
  for (const d of ['site/sdk/', 'site/models/', 'site/vendor/']) assert.ok(ignore.includes(d), d);
});
