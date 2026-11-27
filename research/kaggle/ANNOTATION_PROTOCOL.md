# Independent chart annotation protocol (E01-06, #24)

**Goal.** Ground-truth chart labels that do not come from the model, from SqlVizSpec features or from rule outputs, so the classifier is evaluated against an independent standard (taxonomy: `spec/chart-taxonomy-v1.md`).

## Label space
10 base ONNX classes: kpi, bar, horizontal_bar, stacked_bar, line, area, donut, scatter, heatmap, table. The 21 final outputs are *derived* by the deterministic specializer and are not annotated. Each item gets a `primary` class, a set of `acceptable` classes (primary must be included) and `confidence` 1-3, plus a free-text rationale.

## Independence rules (enforced by `sqltoviz_data.annotations`)
1. Annotators see only the SQL text, column names and a ≤20-row result preview (`tools/make_task_pack.py`); packs containing label/feature/score/rule keys are rejected (`assert_blind`).
2. Annotator type (`human|llm|rule`) is mandatory; `rule` labels are rejected as ground truth. LLM annotators are allowed only if declared as such and reported separately from human labels.
3. Source-corpus chart labels (e.g. nvBench) are *not* shown and never copied into the pack.
4. Two or more annotators per item; ≥2 distinct annotators required for adjudication.

## Quality
Cohen's kappa (pairwise) and Krippendorff's alpha (nominal, handles missing) are computed by the module and unit-tested against hand-derived values. Ties or single-annotator items are flagged `tie_needs_adjudication` / `insufficient_annotators` and are excluded from the test set until resolved. Report kappa/alpha with the number of items; no threshold is claimed as universal.

## Sampling
`build_task_pack` is deterministic given the candidate set and seed and spreads items round-robin across databases to avoid a few schemas dominating (the later split in #26 groups by database).

## Status (2026-11-27)
Protocol, validators, agreement metrics and a blind pack generator are implemented and tested. **No labels exist yet**: a 300-item blind pack was generated from Spider train (seed 20261127) as a smoke test of the tooling, not as labeled data. Human annotation capacity and the LLM-annotator policy must be decided by the project owner before any class-level claim is made; classes absent from public sources (kpi, horizontal_bar, area, heatmap, table) depend entirely on this work (see DECISION_20).
