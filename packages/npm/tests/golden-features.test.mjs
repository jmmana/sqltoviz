import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {extractFeatures, FeatureError} from '../dist/esm/index.js';
import {CONTRACT_SHA256} from '../dist/esm/contract.js';

let dir = dirname(fileURLToPath(import.meta.url));
while (!existsSync(join(dir, 'parity', 'golden_v1.json'))) dir = resolve(dir, '..');
const GOLDEN = JSON.parse(readFileSync(join(dir, 'parity', 'golden_v1.json'), 'utf8'));
const close = (a, b, atol, rtol) => Math.abs(a - b) <= atol + rtol * Math.abs(b);

test('contract pin matches the frozen spec bytes', () => {
  const sha = createHash('sha256').update(readFileSync(join(dir, 'spec', 'sqlvizspec-v1-features.json'))).digest('hex');
  assert.equal(CONTRACT_SHA256, sha);
  assert.equal(GOLDEN.contract_sha256, sha);
});

test('golden features and rejections', () => {
  const {atol, rtol} = GOLDEN;
  let ok = 0, rej = 0; const bad = [];
  for (const c of GOLDEN.cases) {
    const exp = c.expected;
    if (exp.rejected) {
      try { extractFeatures(c.sql, c.schema, c.rows); bad.push([c.case_id, 'expected rejection']); } catch (e) { if (e instanceof FeatureError) rej++; else bad.push([c.case_id, 'wrong error ' + e]); }
      continue;
    }
    let r;
    try { r = extractFeatures(c.sql, c.schema, c.rows); } catch (e) { bad.push([c.case_id, 'unexpected ' + e.message]); continue; }
    exp.table_features.forEach((b, i) => { if (!close(r.table[i], b, atol, rtol)) bad.push([c.case_id, 'table', i, r.table[i], b]); });
    if (r.columns.length !== exp.column_features.length) bad.push([c.case_id, 'columns']);
    exp.column_features.forEach((row, j) => row.forEach((b, i) => { if (!close(r.columns[j][i], b, atol, rtol)) bad.push([c.case_id, 'col', j, i, r.columns[j][i], b]); }));
    ok++;
  }
  assert.deepEqual(bad.slice(0, 10), []);
  assert.equal(ok + rej, GOLDEN.cases.length);
  assert.ok(ok + rej >= 288);
});
