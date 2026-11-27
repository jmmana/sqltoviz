import {test} from 'node:test';import assert from 'node:assert/strict';import {createRequire} from 'node:module';import {recommend,madOutliers,temporalShifts,pareto,pearson,toEcharts,toRecharts} from '../dist/esm/index.js';
test('ESM and CJS',()=>assert.equal(createRequire(import.meta.url)('../dist/cjs/index.js').recommend('SELECT 1',[{x:1}]).chartType,'kpi'));
test('category and adapters',()=>{const rows=[{a:'A',v:2},{a:'B',v:3}],p=recommend('SELECT a,AVG(v)',rows);assert.equal(p.chartType,'bar');assert.deepEqual(toEcharts(p,rows).series[0].data,[2,3]);assert.equal(toRecharts(p,rows).valueKey,'v');});
test('line',()=>assert.equal(recommend('SELECT d,v',[1,2,3,4].map(i=>({d:'2026-01-0'+i,v:i}))).chartType,'line'));
test('duplicates and invalid input',()=>{assert.equal(recommend('SELECT a,v',[{a:'A',v:1},{a:'A',v:2}]).chartType,'table');assert.throws(()=>recommend('SELECT a',[{a:1},{b:2}]));});
test('MAD',()=>{assert.equal(madOutliers([1,2,3,4,100]).outliers[0].index,4);assert.equal(madOutliers([1,1,1,100]).status,'zero_mad');});
test('temporal',()=>{assert.equal(temporalShifts([0,10])[0].status,'zero_baseline');assert.equal(temporalShifts([-10,-5])[0].relative_change,.5);});
test('Pareto',()=>{assert.equal(pareto([1,2]).status,'unknown_additivity');assert.equal(pareto([20,80,0],.8,true).items.filter(x=>x.included).length,1);});
test('Pearson',()=>{assert.ok(Math.abs(pearson([1,2,null,3],[3,2,8,1]).r+1)<1e-12);assert.equal(pearson([1,1,1],[1,2,3]).status,'constant_column');});
