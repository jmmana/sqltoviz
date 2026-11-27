// Golden parity for classification, scores and roles using BOTH ONNX runtimes (onnxruntime-node and onnxruntime-web WASM).
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync, writeFileSync, mkdtempSync, copyFileSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {Engine, BASE_CLASSES, eligible, rulePredict, constrainedChoice, extractFeatures} from '../dist/esm/index.js';
import {loadDefaultEngine, loadEngine, createNodeRunner, bundledModelsDir} from '../dist/esm/node.js';
import {createWebRunner} from '../dist/esm/web.js';

let dir = dirname(fileURLToPath(import.meta.url));
while (!existsSync(join(dir, 'parity', 'golden_v1.json'))) dir = resolve(dir, '..');
const G = JSON.parse(readFileSync(join(dir, 'parity', 'golden_v1.json'), 'utf8'));
const MODELS = bundledModelsDir();
const MANIFEST = JSON.parse(readFileSync(join(MODELS, 'manifest.json'), 'utf8'));
const close = (a, b) => Math.abs(a - b) <= G.atol + G.rtol * Math.abs(b);

async function checkAll(engine, label) {
  let n = 0; const bad = [];
  for (const c of G.cases) {
    const e = c.expected;
    if (e.rejected) continue;
    const r = await engine.recommend(c.sql, c.schema, c.rows);
    BASE_CLASSES.forEach((k, i) => { if (!close(r.scores[k], e.chart_scores[i])) bad.push([label, c.case_id, 'score', k]); });
    if (r.base_class !== e.base_class || r.final_class !== e.final_class || r.constraint_changed !== e.constraint_changed || r.rule_class !== e.rule_class) bad.push([label, c.case_id, 'class', r.base_class, e.base_class, r.final_class, e.final_class]);
    if (JSON.stringify(r.eligible) !== JSON.stringify(e.eligible)) bad.push([label, c.case_id, 'eligible']);
    if (JSON.stringify(r.roles.map((x) => x.role)) !== JSON.stringify(e.roles)) bad.push([label, c.case_id, 'roles']);
    r.roles.forEach((x, j) => x.scores.forEach((v, i) => { if (!close(v, e.role_scores[j][i])) bad.push([label, c.case_id, 'role score', j, i]); }));
    n++;
  }
  assert.deepEqual(bad.slice(0, 8), []);
  assert.equal(n, G.cases.filter((c) => !c.expected.rejected).length);
}

test('Node runtime (onnxruntime-node): all golden scores, classes, eligibility and roles', async () => checkAll(await loadDefaultEngine(), 'node'));

test('Browser WASM runtime (onnxruntime-web, single thread): all golden scores, classes and roles', async () => {
  const chart = await createWebRunner(new Uint8Array(readFileSync(join(MODELS, MANIFEST.chart.file))), MANIFEST.chart.sha256, 'chart');
  const role = await createWebRunner(new Uint8Array(readFileSync(join(MODELS, MANIFEST.role.file))), MANIFEST.role.sha256, 'role');
  await checkAll(new Engine({chart, role, chartStatus: MANIFEST.chart.status}), 'wasm');
});

test('results are labelled experimental and models are replaceable without API change', async () => {
  const e = await loadDefaultEngine();
  const r = await e.recommend('SELECT a FROM t', ['a'], [[1]]);
  assert.equal(r.model_status, 'experimental');
  assert.ok(r.warnings.some((w) => w.includes('not scientifically validated')));
  const d = mkdtempSync(join(tmpdir(), 'sqltoviz-'));
  for (const k of ['chart', 'role']) copyFileSync(join(MODELS, MANIFEST[k].file), join(d, 'final_' + MANIFEST[k].file));
  const man = {chart: {file: 'final_' + MANIFEST.chart.file, sha256: MANIFEST.chart.sha256, status: 'validated'}, role: {file: 'final_' + MANIFEST.role.file, sha256: MANIFEST.role.sha256, status: 'validated'}};
  const f = await loadEngine(man, d);
  const r2 = await f.recommend('SELECT a FROM t', ['a'], [[1]]);
  assert.equal(r2.model_status, 'validated');
  assert.ok(!r2.warnings.some((w) => w.includes('not scientifically validated')));
  assert.deepEqual(Object.keys(r2).sort(), Object.keys(r).sort());
});

test('checksum and schema enforcement; rules-only engine', async () => {
  await assert.rejects(createNodeRunner(join(MODELS, MANIFEST.chart.file), '0'.repeat(64), 'chart'), /checksum/);
  await assert.rejects(createNodeRunner(join(MODELS, MANIFEST.chart.file), MANIFEST.chart.sha256, 'role'), /incompatible/);        // chart model loaded as role model
  await assert.rejects(createWebRunner(new Uint8Array([1, 2, 3]), '0'.repeat(64), 'chart'), /checksum/);
  const r = await new Engine().recommend('SELECT SUM(x) AS s FROM t', ['s'], [[3]]);
  assert.deepEqual([r.final_class, r.scores, r.roles], ['kpi', null, null]);
  assert.match(r.warnings[0], /rules-only/);
});

test('constraints and rules match the golden reference without any model', () => {
  for (const c of G.cases) {
    const e = c.expected;
    if (e.rejected) continue;
    const {table, columns} = extractFeatures(c.sql, c.schema, c.rows);
    assert.equal(rulePredict(table, columns), e.rule_class, c.case_id);
    assert.deepEqual(eligible(table, columns), e.eligible, c.case_id);
    const r = constrainedChoice(e.chart_scores, table, columns);
    assert.deepEqual([r.cls, r.changed], [e.final_class, e.constraint_changed], c.case_id);
  }
});
