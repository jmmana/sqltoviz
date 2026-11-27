// Model-backed recommendation engine. The learned models are injected as `ModelRunner`s, so the public API is identical for the
// bundled EXPERIMENTAL candidate models and for future final models (just load different files / a different manifest).
import {BASE_CLASSES, CONTRACT_SHA256, CONTRACT_VERSION, ROLES} from "./contract.js";
import {extractFeatures, type Cell, type ColumnSpec} from "./features.js";
import {constrainedChoice, eligible, rulePredict, type BaseClass} from "./rules.js";

/** Runs a float32 model: `input` is rows x cols (row-major), returns rows x outputs (row-major). */
export interface ModelRunner { run(input: Float32Array, rows: number, cols: number): Promise<Float32Array> }
export interface ModelManifestEntry { file: string; sha256: string; status: string; version?: string }
export interface ModelManifest { chart?: ModelManifestEntry; role?: ModelManifestEntry }
export interface Recommendation {
  contract_version: string; contract_sha256: string; model_status: string; base_class: BaseClass; final_class: BaseClass;
  constraint_changed: boolean; rule_class: BaseClass; scores: Record<string, number> | null; eligible: Record<string, boolean>;
  roles: {column: string; role: string; scores: number[]}[] | null; table_features: Float32Array; column_features: Float32Array[]; warnings: string[];
}
export interface EngineOptions { chart?: ModelRunner; role?: ModelRunner; chartStatus?: string }

const argmax = (a: ArrayLike<number>) => { let k = 0; for (let i = 1; i < a.length; i++) if (a[i] > a[k]) k = i; return k; };

export class Engine {
  constructor(private readonly opts: EngineOptions = {}) {}
  get modelStatus(): string { return this.opts.chart ? this.opts.chartStatus ?? "unknown" : "none (rules only)"; }
  async recommend(sql: string, columns: (string | ColumnSpec)[], rows: Cell[][]): Promise<Recommendation> {
    const schema: ColumnSpec[] = columns.map((c) => (typeof c === "string" ? {name: c} : c));
    const {table, columns: colmat} = extractFeatures(sql, schema, rows);
    const ruleClass = rulePredict(table, colmat), el = eligible(table, colmat), warnings: string[] = [];
    let scores: number[] | null = null, base: BaseClass = ruleClass, final: BaseClass = ruleClass, changed = false;
    if (!this.opts.chart) warnings.push("No chart model loaded: rules-only recommendation.");
    else {
      const out = await this.opts.chart.run(table, 1, 32);
      scores = Array.from(out.subarray(0, BASE_CLASSES.length), Number);
      base = BASE_CLASSES[argmax(scores)];
      const r = constrainedChoice(scores, table, colmat);
      final = r.cls; changed = r.changed;
    }
    let roles: Recommendation["roles"] = null;
    if (this.opts.role) {
      const flat = new Float32Array(colmat.length * 28);
      colmat.forEach((r, j) => flat.set(r, j * 28));
      const out = await this.opts.role.run(flat, colmat.length, 28);
      roles = schema.map((c, j) => { const s = Array.from(out.subarray(j * 5, j * 5 + 5), Number); return {column: c.name, role: ROLES[argmax(s)], scores: s}; });
    }
    const status = this.modelStatus;
    if (status !== "validated") warnings.push(`Model status: ${status}. Recommendations are not scientifically validated.`);
    return {contract_version: CONTRACT_VERSION, contract_sha256: CONTRACT_SHA256, model_status: status, base_class: base, final_class: final,
      constraint_changed: changed, rule_class: ruleClass, scores: scores ? Object.fromEntries(BASE_CLASSES.map((k, i) => [k, scores![i]])) : null,
      eligible: el, roles, table_features: table, column_features: colmat, warnings};
  }
}
