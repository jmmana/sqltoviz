// Runs golden fixtures through the INSTALLED @sqltoviz/core tarball. Usage: node run_node.mjs GOLDEN OUT (cwd = clean project dir)
import {readFileSync, writeFileSync, readdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {join} from 'node:path';
const {BASE_CLASSES} = await import('@sqltoviz/core');
const {loadDefaultEngine, bundledModelsDir} = await import('@sqltoviz/core/node');
const golden = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const engine = await loadDefaultEngine();
const dir = bundledModelsDir();
const models = {};
for (const f of readdirSync(dir).filter((n) => n.endsWith('.onnx')).sort()) models[f] = createHash('sha256').update(readFileSync(join(dir, f))).digest('hex');
const pkg = JSON.parse(readFileSync(join(dir, '..', 'package.json'), 'utf8'));
const cases = {};
for (const c of golden.cases) {
  let r;
  try { r = await engine.recommend(c.sql, c.schema, c.rows); } catch (e) { cases[c.case_id] = {rejected: true}; continue; }
  cases[c.case_id] = {model_status: r.model_status, base_class: r.base_class, final_class: r.final_class, rule_class: r.rule_class,
    constraint_changed: r.constraint_changed, eligible: r.eligible, scores: BASE_CLASSES.map((k) => r.scores[k]),
    roles: r.roles.map((x) => x.role), role_scores: r.roles.map((x) => x.scores)};
}
writeFileSync(process.argv[3], JSON.stringify({package: `${pkg.name} ${pkg.version}`, location: dir, models, cases}));
