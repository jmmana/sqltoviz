import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {specializeOutputs, OUTPUTS_SHA256, BASE_CONTRACT_SHA256} from '../dist/esm/index.js';

let dir = dirname(fileURLToPath(import.meta.url));
while (!existsSync(join(dir, 'parity', 'outputs_v1.json'))) dir = resolve(dir, '..');
const FIX = JSON.parse(readFileSync(join(dir, 'parity', 'outputs_v1.json'), 'utf8'));
const sha = (f) => createHash('sha256').update(readFileSync(join(dir, 'spec', f))).digest('hex');
const close = (a, b) => Math.abs(a - b) <= FIX.atol + FIX.rtol * Math.abs(b);

// Params compare within tolerance; output, encodings, rejected and fallback_chain compare exactly.
function same(a, b, path, bad) {
  if (typeof b === 'number' && typeof a === 'number') { if (!close(a, b)) bad.push(`${path}: ${a} != ${b}`); }
  else if (Array.isArray(b)) { if (!Array.isArray(a) || a.length !== b.length) bad.push(`${path}: length`); else b.forEach((x, i) => same(a[i], x, `${path}[${i}]`, bad)); }
  else if (b && typeof b === 'object') { if (!a || typeof a !== 'object' || Object.keys(a).sort().join() !== Object.keys(b).sort().join()) bad.push(`${path}: keys ${a && Object.keys(a)} != ${Object.keys(b)}`); else for (const k of Object.keys(b)) same(a[k], b[k], `${path}.${k}`, bad); }
  else if (a !== b) bad.push(`${path}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`);
}

test('outputs contract pins match the spec bytes', () => {
  assert.equal(OUTPUTS_SHA256, sha('sqlvizspec-v1-outputs.json'));
  assert.equal(BASE_CONTRACT_SHA256, sha('sqlvizspec-v1-features.json'));
  assert.equal(FIX.outputs_sha256, OUTPUTS_SHA256);
});

test('outputs v1 fixtures replay', () => {
  let ok = 0; const bad = [];
  for (const c of FIX.cases) {
    const r = specializeOutputs(c.columns, c.rows, c.metadata, c.base_scores, c.roles, c.base_eligibility), e = c.expected, n = bad.length;
    for (const k of ['output', 'encodings', 'rejected', 'fallback_chain']) assert.deepEqual(r[k], e[k], `${c.id}: ${k}`);
    same(r.params, e.params, `${c.id}.params`, bad);
    if (bad.length === n) ok++;
  }
  assert.deepEqual(bad.slice(0, 10), []);
  assert.equal(ok, FIX.cases.length);
  assert.equal(FIX.cases.length, 120);
});
