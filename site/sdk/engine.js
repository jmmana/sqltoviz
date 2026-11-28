// Model-backed recommendation engine. The learned models are injected as `ModelRunner`s, so the public API is identical for the
// bundled EXPERIMENTAL candidate models and for future final models (just load different files / a different manifest).
import { BASE_CLASSES, CONTRACT_SHA256, CONTRACT_VERSION, ROLES } from "./contract.js";
import { extractFeatures } from "./features.js";
import { constrainedChoice, eligible, rulePredict } from "./rules.js";
const argmax = (a) => { let k = 0; for (let i = 1; i < a.length; i++)
    if (a[i] > a[k])
        k = i; return k; };
export class Engine {
    opts;
    constructor(opts = {}) {
        this.opts = opts;
    }
    get modelStatus() { return this.opts.chart ? this.opts.chartStatus ?? "unknown" : "none (rules only)"; }
    async recommend(sql, columns, rows) {
        const schema = columns.map((c) => (typeof c === "string" ? { name: c } : c));
        const { table, columns: colmat } = extractFeatures(sql, schema, rows);
        const ruleClass = rulePredict(table, colmat), el = eligible(table, colmat), warnings = [];
        let scores = null, base = ruleClass, final = ruleClass, changed = false;
        if (!this.opts.chart)
            warnings.push("No chart model loaded: rules-only recommendation.");
        else {
            const out = await this.opts.chart.run(table, 1, 32);
            scores = Array.from(out.subarray(0, BASE_CLASSES.length), Number);
            base = BASE_CLASSES[argmax(scores)];
            const r = constrainedChoice(scores, table, colmat);
            final = r.cls;
            changed = r.changed;
        }
        let roles = null;
        if (this.opts.role) {
            const flat = new Float32Array(colmat.length * 28);
            colmat.forEach((r, j) => flat.set(r, j * 28));
            const out = await this.opts.role.run(flat, colmat.length, 28);
            roles = schema.map((c, j) => { const s = Array.from(out.subarray(j * 5, j * 5 + 5), Number); return { column: c.name, role: ROLES[argmax(s)], scores: s }; });
        }
        const status = this.modelStatus;
        if (status !== "validated")
            warnings.push(`Model status: ${status}. Recommendations are not scientifically validated.`);
        return { contract_version: CONTRACT_VERSION, contract_sha256: CONTRACT_SHA256, model_status: status, base_class: base, final_class: final,
            constraint_changed: changed, rule_class: ruleClass, scores: scores ? Object.fromEntries(BASE_CLASSES.map((k, i) => [k, scores[i]])) : null,
            eligible: el, roles, table_features: table, column_features: colmat, warnings };
    }
}
