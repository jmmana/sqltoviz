import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { test } from 'node:test';
import { recommend } from './preview.mjs';
import { scenarios } from './scenarios.mjs';

test('four bilingual scenarios are available', () => {
  assert.equal(Object.keys(scenarios).length, 4);
  for (const { labels } of Object.values(scenarios)) {
    assert.ok(labels.en && labels.es);
  }
});

for (const [id, scenario] of Object.entries(scenarios)) {
  test(`scenario ${id} reproduces its rows and recommendation`, () => {
    const database = new DatabaseSync(':memory:');
    try {
      database.exec(readFileSync(new URL('./scenarios.sql', import.meta.url), 'utf8'));
      const rows = database.prepare(scenario.sql).all().map(row => ({ ...row }));
      assert.deepEqual(rows, scenario.rows);
      const plan = recommend(scenario.sql, rows);
      assert.equal(plan.chartType, scenario.chartType);
      assert.equal(plan.warnings.length, scenario.warningCount);
    } finally {
      database.close();
    }
  });
}
