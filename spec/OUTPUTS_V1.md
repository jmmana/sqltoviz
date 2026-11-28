# SqlVizSpec-Outputs-v1.0.0 (additive extension)

Issues #3, #36, #40, #44, #108. This document records the decision and how to consume the artifacts. It makes no claim about model quality.

## Decision

* The base contract `SqlVizSpec-v1.0.0` (`spec/sqlvizspec-v1-features.json`, SHA256 `d14d140b9118c0b535d4e504af7f16546f47d56ac8f1692c2ab62615686e5864`), the shipped ONNX models and `parity/golden_v1.json` are **untouched**. The 10 base classes stay the model output space.
* The 21 concrete outputs are a separately versioned, separately pinned artifact: `spec/sqlvizspec-v1-outputs.json`, version `SqlVizSpec-Outputs-v1.0.0`, SHA256 `45581c7b4414fc6250fb57988e04811bc4492fb1bbc21841058589481cce01db`, with `base_contract_sha256` binding it to the base hash. `spec/verify_contract.py` checks both and CI runs it.
* No model decides a specialization. Each output is chosen by deterministic preconditions evaluated in a fixed order; unknown semantics fail closed (metadata that is absent or malformed counts as "not declared").

Why additive: retraining or re-pinning the base contract would invalidate the models and every golden expectation. Extending the output space downstream of the base class keeps all three runtimes verifiable against the old artifacts.

## Outputs and priority

21 outputs: kpi (legacy alias `kpi_card`), gauge, bar, horizontal_bar, grouped_bar, stacked_bar, waterfall, line, area, stacked_area, combo_dual_axis, donut, treemap, sunburst, scatter, bubble, heatmap, histogram, boxplot, violin, table.

Specialization (most specific first): kpi: gauge, kpi; bar: waterfall, grouped_bar, treemap, violin, boxplot, histogram, bar; horizontal_bar: horizontal_bar; stacked_bar: stacked_bar; line: combo_dual_axis, line; area: stacked_area, area; donut: sunburst, treemap, donut; scatter: bubble, scatter; heatmap: heatmap; table: table.

Candidate order: base classes ranked by `base_scores` (descending, ties and absent scores in contract order), each expanded in the order above, an output already evaluated is skipped, evaluation stops at the first output whose preconditions all pass, `table` is the terminal fallback. `rejected` holds the first failing reason code of every candidate tried before the winner; `fallback_chain` lists the candidates tried, ending with the winner.

Per-output precondition ids, reason codes and encoding channels live in `outputs_definition` of the spec JSON (the single source of truth; the generated constants carry them).

### Gate
Outputs with `requires_base_eligibility` need at least one of their carrying base classes (e.g. treemap: bar or donut) to be eligible under the existing `rules.eligible`. histogram, boxplot and violin skip the gate (raw-sample shape) but require declared raw samples (`raw_samples` metadata), otherwise a 40-row aggregated bar chart would be misread as a distribution.

### Thresholds
max 25 categories for bar variants; min 30 samples histogram and violin; min 5 per group boxplot; line/area min 3 rows; donut 2..12 slices; heatmap max 50 categories per axis; treemap max 200 leaves; histogram bins by Sturges `ceil(log2 n)+1`; quantiles by linear interpolation (type 7); Tukey whiskers at 1.5 IQR; violin uses a Gaussian KDE with Silverman bandwidth `0.9*min(sd, IQR/1.34)*n^(-1/5)` (sd with n-1; IQR 0 falls back to sd). Numeric params are compared at `atol = rtol = 1e-6`: waterfall sum/total/diff, histogram n/bins/min/max/width, boxplot quartiles and whiskers, violin bandwidth, donut total.

### Decisions I took where the brief left room (flagged for review)
1. Distribution outputs are disjoint by grouping: boxplot and violin require a declared group column with at least 2 groups; histogram pools all samples. Without this, violin (ungrouped, 30+ samples) would always shadow boxplot and histogram given the mandated priority order.
2. Violin needs 30 samples per group, boxplot 5 per group; a mixed case (some group under 30) falls to boxplot.
3. Dual axes never inspect the scale ratio: they require both measures to have metadata entries, a unit and a label each, `axis: left` on one and `axis: right` on the other, and distinct columns with non-identical values.
4. With the mandated order, a declared two-level hierarchy reached through the **bar** base can be answered by grouped_bar before treemap (both are valid shapes). Through the **donut** base sunburst/treemap win first. Fixtures document both paths.
5. Rows with a missing value in any column an aggregate output uses are rejected (`missing_values`); raw-sample outputs drop missing measures and count only the rest.

## Metadata (all optional)
```
columns: {name: {unit?: str, additive?: bool, axis?: "left"|"right", label?: str, kind?: "bin"|"quantile"}}
groups_disjoint: bool            groups_exhaustive: bool
goal: {value: number | column: name, bounds: [lo, hi]}
waterfall: {order_by: column name, total: number}
hierarchy: {levels: [column names], weight: column name}
raw_samples: true | {column: name, group?: name}
missing_cells: "zero" | "blank"
```
Only a literal JSON `true` counts for booleans.

## API (Python reference; TypeScript and .NET follow in phase 2)
`specialize_outputs(columns, rows, metadata=None, base_scores=None, roles=None, base_eligibility)` returns
`{output, encodings, params, rejected: [{output, reason_code}], fallback_chain}`.
`columns` carry resolved types (`resolve_column_types` fills them with the base contract rules); `base_scores` is `{class: score}` or a list aligned with `BASE_CLASSES`; `roles` is `{column: role}` (only `x_axis`, `y_axis`, `color_series`, `size_or_secondary` as preferences, `ignore_tooltip` excludes a column); `base_eligibility` is `{class: bool}` from the base rules and is required (missing class = ineligible). `params` is an addition to the brief's shape and carries the compared numbers.

## Fixtures
`parity/outputs_v1.json` (120 cases) holds input, base eligibility and expected result per case, plus `outputs_sha256` and `base_contract_sha256`. Regenerate with `python parity/tools/gen_outputs.py` (`--check` in CI). Each case has `kind` (positive: the target is chosen; negative: the target is rejected with a stated reason; edge: recorded behaviour only) and `target`. A port replays every case and must match `output`, `encodings`, `rejected`, `fallback_chain` exactly and `params` within tolerance.

Honest limits: expectations come from the Python reference itself, so the fixtures prove cross-runtime agreement, not that the rules are right; rule thresholds are design choices, not validated findings. Support (number of fixtures, not accuracy):

| output | positive | negative | edge |
|---|---|---|---|
| kpi | 2 | 1 | 2 |
| gauge | 2 | 4 | 2 |
| bar | 2 | 2 | 9 |
| horizontal_bar | 1 | 1 | 0 |
| grouped_bar | 1 | 2 | 0 |
| stacked_bar | 2 | 4 | 0 |
| waterfall | 1 | 4 | 1 |
| line | 1 | 2 | 2 |
| area | 1 | 1 | 0 |
| stacked_area | 1 | 3 | 0 |
| combo_dual_axis | 2 | 6 | 0 |
| donut | 1 | 5 | 1 |
| treemap | 2 | 5 | 0 |
| sunburst | 1 | 2 | 0 |
| scatter | 1 | 2 | 1 |
| bubble | 1 | 3 | 0 |
| heatmap | 2 | 3 | 0 |
| histogram | 2 | 5 | 3 |
| boxplot | 3 | 5 | 0 |
| violin | 1 | 4 | 1 |
| table | 1 | 0 | 3 |
