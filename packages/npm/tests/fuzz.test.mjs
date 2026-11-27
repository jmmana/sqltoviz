// Differential fuzz: replays random cases whose expected values were produced by the Python SDK (parity/tools/gen_fuzz.py).
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {extractFeatures, FeatureError} from '../dist/esm/index.js';
const file = process.env.SQLTOVIZ_FUZZ;
test('differential fuzz vs Python SDK', {skip: !file || !existsSync(file) ? 'set SQLTOVIZ_FUZZ=<file from parity/tools/gen_fuzz.py>' : false}, () => {
  const G = JSON.parse(readFileSync(file, 'utf8'));
  const close = (a, b) => Math.abs(a - b) <= G.atol + G.rtol * Math.abs(b);
  const bad = []; let ok = 0, rej = 0;
  for (const c of G.cases) {
    let r = null, err = null;
    try { r = extractFeatures(c.sql, c.schema, c.rows); } catch (e) { if (e instanceof FeatureError) err = e; else { bad.push([c.case_id, 'crash', String(e)]); continue; } }
    if (c.expected.rejected) { if (!err) bad.push([c.case_id, 'expected rejection']); else rej++; continue; }
    if (err) { bad.push([c.case_id, 'unexpected rejection', err.message]); continue; }
    c.expected.table_features.forEach((b, i) => { if (!close(r.table[i], b)) bad.push([c.case_id, 'table', i, r.table[i], b, c.sql]); });
    c.expected.column_features.forEach((row, j) => row.forEach((b, i) => { if (!close(r.columns[j][i], b)) bad.push([c.case_id, 'col', j, i, r.columns[j][i], b, c.sql]); }));
    ok++;
  }
  assert.deepEqual(bad.slice(0, 5), []);
  console.log(`fuzz: ${ok} accepted, ${rej} rejected`);
});
