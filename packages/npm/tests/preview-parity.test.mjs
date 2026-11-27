import {test} from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {recommend,madOutliers,temporalShifts,pareto,pearson} from '../dist/esm/index.js';
const f=JSON.parse(readFileSync(new URL('../../../parity/preview-v0.1.json',import.meta.url),'utf8'));
for(const c of f.charts)test('fixture '+c.id,()=>{const p=recommend(c.sql,c.rows);assert.deepEqual([p.chartType,p.encodings.x,p.encodings.y],[c.chart,c.x,c.y]);});
test('shared statistics',()=>{const s=f.statistics;
for(const c of s.mad){const p=madOutliers(c.values);assert.equal(p.status,c.status);assert.deepEqual(p.outliers.map(x=>x.index),c.indices);}
for(const c of s.temporal){const p=temporalShifts(c.values);assert.deepEqual(p.map(x=>x.status),c.statuses);assert.deepEqual(p.map(x=>x.relative_change),c.changes);}
for(const c of s.pareto){const p=pareto(c.values,.8,c.additive);assert.equal(p.status,c.status);assert.deepEqual(p.items.filter(x=>x.included).map(x=>x.index),c.indices);}
for(const c of s.pearson){const p=pearson(c.xs,c.ys);assert.equal(p.status,c.status);if(c.r===null)assert.equal(p.r,null);else assert.ok(Math.abs(p.r-c.r)<=f.tolerance);}
});
