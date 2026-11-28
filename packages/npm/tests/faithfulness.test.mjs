// Replays parity/tools/gen_faithfulness.py cases (SQLTOVIZ_FAITH=<file>); errors measured against exact rational/decimal references.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {madOutliers, pearson, temporalShifts, pareto} from '../dist/esm/index.js';
const file = process.env.SQLTOVIZ_FAITH;
const rel = (a, b) => Math.abs(a - b) / Math.max(Math.abs(b), 1e-300);
test('statistical detectors match exact references', {skip: !file || !existsSync(file) ? 'set SQLTOVIZ_FAITH' : false}, () => {
  const G = JSON.parse(readFileSync(file, 'utf8')), tol = G.tolerance, worst = {mad: 0, pearson: 0, temporal: 0, pareto: 0};
  const upd = (k, v) => { worst[k] = Math.max(worst[k], v); };
  for (const c of G.cases) {
    const e = c.expected;
    if (c.kind === 'mad') {
      const r = madOutliers(c.values); assert.equal(r.status, e.status);
      if (e.status === 'ok' || e.status === 'zero_mad') { upd('mad', e.median ? rel(r.median, e.median) : Math.abs(r.median)); upd('mad', e.mad ? rel(r.mad, e.mad) : Math.abs(r.mad)); }
      assert.deepEqual(r.outliers.map((o) => o.index), e.outliers.map((o) => o.index));
      r.outliers.forEach((o, i) => upd('mad', rel(o.score, e.outliers[i].score)));
    } else if (c.kind === 'pearson') {
      const r = pearson(c.xs, c.ys); assert.equal(r.status, e.status);
      if (e.status === 'ok') upd('pearson', Math.abs(r.r - e.r));
    } else if (c.kind === 'temporal') {
      const r = temporalShifts(c.values); assert.deepEqual(r.map((x) => x.status), e.map((x) => x.status));
      r.forEach((x, i) => { if (e[i].delta !== null) upd('temporal', e[i].delta ? rel(x.delta, e[i].delta) : Math.abs(x.delta)); if (e[i].relative_change !== null) upd('temporal', e[i].relative_change ? rel(x.relative_change, e[i].relative_change) : Math.abs(x.relative_change)); });
    } else {
      const r = pareto(c.values, c.coverage, true); assert.equal(r.status, e.status);
      assert.deepEqual(r.items.map((i) => i.index), e.items.map((i) => i.index)); assert.deepEqual(r.items.map((i) => i.included), e.items.map((i) => i.included));
      r.items.forEach((x, i) => { upd('pareto', Math.abs(x.share - e.items[i].share)); upd('pareto', Math.abs(x.cumulative - e.items[i].cumulative)); });
    }
  }
  console.log('typescript worst errors', JSON.stringify(worst));
  assert.ok(Math.max(worst.mad, worst.temporal) < tol.relative && worst.pearson < tol.pearson_abs && worst.pareto < 1e-12, JSON.stringify(worst));
});
