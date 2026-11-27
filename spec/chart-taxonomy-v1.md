# SqlVizSpec-v1 — chart taxonomy (approved scope, draft implementation contract)

20 visualization types plus table fallback. Supersedes the original eight-class output proposal; training and SDK implementation must use this contract. Legacy kpi_card is accepted as input alias for kpi.

| Output | Base candidate / specialization | Eligibility |
|---|---|---|
| kpi | kpi | scalar metric or comparable periods |
| gauge | kpi | explicit target and bounds |
| bar | bar | categorical comparison |
| horizontal_bar | horizontal_bar | ranking or long labels |
| grouped_bar | bar | multiple comparable series; no unsafe stacking |
| stacked_bar | stacked_bar | additive measures, disjoint groups, consistent units |
| waterfall | bar | ordered signed contributions reconciled with total |
| line | line | ordered temporal or sequential values |
| area | area | meaningful magnitude and baseline |
| stacked_area | area | additive disjoint series, aligned periods |
| combo_dual_axis | line/bar | distinct meaningful metrics, explicit units and axis labels; scale alone insufficient |
| donut | donut | mutually exclusive exhaustive parts, nonnegative, positive total |
| treemap | bar/donut | validated hierarchy and additive positive weights |
| sunburst | donut | validated multilevel hierarchy and additive weights |
| scatter | scatter | paired quantitative observations |
| bubble | scatter | third nonnegative quantitative measure mapped to marker area |
| heatmap | heatmap | two dimensions and a metric, explicit missing cells |
| histogram | bar | raw samples or valid ordered bins with frequencies |
| boxplot | bar | raw samples or sufficient quantiles and defined whiskers |
| violin | bar | sufficient raw samples and specified density estimator |
| table | table | fallback or detail |

## Model contract
Ten base candidates ordered: kpi, bar, horizontal_bar, stacked_bar, line, area, donut, scatter, heatmap, table. chart scores shape [batch,10]; role scores remain [M,5] pending role contract review. Final output enum has 21 values. Evaluate whether five roles suffice for hierarchy, secondary axis and size; allow explicit auxiliary encoding fields. Do not confuse base scores with final-class calibrated confidence.

## Pipeline
Extract SQL and data features; rank base candidates; evaluate specialization predicates (including candidates outside top-1); enforce hard semantic constraints; choose highest eligible ranked alternative or table. Unknown semantics fail closed for risky charts. Metadata may supply units, goal, hierarchy, grain and additivity. SQL syntax alone cannot prove disjointness or additivity. SUM can still double count; COUNT DISTINCT is not generally additive. AVG and ratios require correct weights or denominators for recomposition. Simple non-stacked area is not automatically forbidden for averages. Thresholds such as cardinality or 0.55 confidence are tunable hypotheses, not universal rules. Complexity of profiling and density estimation is measured separately from fixed-size rule evaluation.

## Explainability
Return selected chart, base candidate scores, rule IDs, rejected alternatives, reason codes, spec version and warnings. Examples: NON_ADDITIVE_METRIC, MISSING_TARGET, INSUFFICIENT_SAMPLES, INVALID_HIERARCHY, UNKNOWN_UNITS. Never invent missing metadata.

## Acceptance
All 21 outputs demonstrated with positive and negative fixtures; test ambiguous SQL, aliases, nested aggregates, duplicate groups and missing metadata. Maintain cross-language parity on at least 250 fixtures with coverage of all outputs and rejection rules. Evaluate base classifier and end-to-end 21-output macro-F1, per-class support, semantic violation rate, fallback coverage and latency. Compare flat classifier, hierarchical model and rules-only baselines with independent labels and grouped holdouts. No claim of novelty or performance before literature review and experiments.

## Español
20 visualizaciones más tabla de respaldo. El modelo predice diez clases base; un motor determinista especializa y valida las recomendaciones. Si no se puede demostrar aditividad, jerarquía, unidades u objetivo, se descarta el gráfico que requiere esa evidencia. No se publican métricas hasta completar los experimentos.
