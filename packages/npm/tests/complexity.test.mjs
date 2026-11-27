// Complexity guard (#36): extraction is O(N log N); a 10x larger input must not be ~100x slower (bound 40x, expected ~10-13x).
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {performance} from 'node:perf_hooks';
import {extractFeatures} from '../dist/esm/index.js';
const SQL = 'SELECT category, region, SUM(value) AS value, day FROM t GROUP BY category, region, day ORDER BY day';
const SCHEMA = [{name: 'category'}, {name: 'region'}, {name: 'value'}, {name: 'day'}];
const rows = (n) => Array.from({length: n}, (_, i) => [`cat${(i * 7) % 12}`, `reg${(i * 3) % 5}`, ((i * 37) % 1000) + ((i * 13) % 100) / 100, `2024-${String(1 + i % 12).padStart(2, '0')}-${String(1 + i % 27).padStart(2, '0')}`]);
const best = (n, reps = 7) => { const r = rows(n); let b = Infinity; for (let i = 0; i < reps; i++) { const t = performance.now(); extractFeatures(SQL, SCHEMA, r); b = Math.min(b, performance.now() - t); } return b; };
test('feature extraction scales near-linearly (10x rows < 40x time)', () => {
  best(2000, 3);                               // warm-up (JIT)
  const small = best(2000), large = best(20000);
  assert.ok(large / small < 40, `10x rows took ${(large / small).toFixed(1)}x longer`);
});
