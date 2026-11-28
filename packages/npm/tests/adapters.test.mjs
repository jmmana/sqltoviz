import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { test } from 'node:test';
import * as esm from '../dist/esm/index.js';

const cjs = createRequire(import.meta.url)('../dist/cjs/index.js');

for (const [entry, sdk] of Object.entries({ esm, cjs })) {
  test(`${entry} horizontal bars use the numeric X axis`, () => {
    const rows = Array.from({ length: 13 }, (_, index) => ({
      category: `Group ${index}`,
      amount: -index,
    }));
    const plan = sdk.recommend('SELECT category, amount FROM totals', rows);
    assert.equal(plan.chartType, 'horizontal_bar');
    const options = sdk.toEcharts(plan, rows);
    assert.equal(options.xAxis.type, 'value');
    assert.deepEqual(options.yAxis.data, rows.map(row => row.category));
    assert.deepEqual(options.series[0].data, rows.map(row => row.amount));
    const recharts = sdk.toRecharts(plan, rows);
    assert.equal(recharts.chart, 'BarChart');
    assert.equal(recharts.layout, 'vertical');
    assert.equal(recharts.categoryKey, 'category');
    assert.equal(recharts.valueKey, 'amount');
  });

  test(`${entry} chronological results use line charts`, () => {
    const rows = [1, 2, 3, 4].map(value => ({ day: `2026-01-0${value}`, value }));
    const plan = sdk.recommend('SELECT day, value FROM totals ORDER BY day', rows);
    assert.equal(sdk.toEcharts(plan, rows).series[0].type, 'line');
    assert.equal(sdk.toRecharts(plan, rows).chart, 'LineChart');
  });
}
