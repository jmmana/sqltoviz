# Pre-registered evaluation protocol (E08-03, #91)

Version 1.0. Frozen by git tag `prereg-v1` on the commit that introduces this file; the tag's commit SHA is recorded in the issue #91 comment. Any later deviation must be listed in the paper under "Deviations from protocol" with the commit that introduced it.

## 1. What is already seen (transparency)
Before freezing, these analyses were run and therefore are **exploratory**, not confirmatory: synthetic E1 (3 split seeds), leave-one-group-out ablation (synthetic), LLM-labelled pilot E2/E3 (300 Spider-train queries, 100 reserved), role feasibility on Vega-Lite specs, ONNX parity (Python), leakage audit. Outputs: `research/kaggle/EXPERIMENTS.md`, `reports/`. **Unseen and confirmatory:** the 100 reserved items (human labels, not yet collected), all evaluations that use human labels, latency/memory (RQ6), anomaly faithfulness (RQ8), TypeScript/.NET parity.

## 2. Pinned artifacts
Contract SqlVizSpec-v1.0.0 SHA256 `d14d140b9118c0b535d4e504af7f16546f47d56ac8f1692c2ab62615686e5864`; interpretation document `research/kaggle/FEATURE_INTERPRETATIONS.md` (confirmed normative; SHA256 recorded in every report); taxonomy `spec/chart-taxonomy-v1.md`; data manifests `research/kaggle/manifests/`; Vega-Lite commit `research/kaggle/manifests/vega_lite_pin.txt`; random seed 20261127 (split seeds 0,1,2).

## 3. Data and label sources (never merged)
| Source | Use | Evaluation role |
|---|---|---|
| synthetic (by construction) | training; E1 | exploratory only |
| LLM annotators (two families, blind) | pilot labels | exploratory; reported as LLM agreement, never as human |
| human annotators (>=2, independent, blind workbook) | **confirmatory evaluation** on the 100 reserved items (+ any further batch) | primary |
| Vega-Lite expert specs | role supervision | RQ7 |
The 100 reserved items are excluded from all training and from every LLM-label experiment. Human agreement is reported (Cohen's kappa, percent agreement); items without human majority are adjudicated by discussion and flagged; a class with fewer than 5 human-labelled items is reported but excluded from macro-F1 (and listed).

## 4. Systems compared
Rules-only (thresholds fixed in `rules.py` at the freezing commit), SQL-only RF, data-only RF, hybrid RF (32 contract features), hybrid + hard semantic constraints. Random forest with the fixed defaults in `experiment.make_rf` (300 trees, min leaf 2, balanced class weights, n_jobs=1); **no hyper-parameter tuning**. The final model is trained on all synthetic data (and, if explicitly stated, on non-reserved LLM-labelled items), never on reserved items.

## 5. Metrics and statistics
Primary: macro-F1 over classes with human support (plus accuracy, per-class P/R/F1/support, confusion matrix, "acceptable-set" hit rate, semantic violation rate, table-fallback rate, majority-class baseline). Uncertainty: cluster bootstrap over databases, 2000 resamples, percentile 95 % CI; system differences by paired cluster bootstrap on the same resamples; multiple comparisons: all pairwise differences reported, no selective reporting; claims require the CI of the difference to exclude 0. Role model: macro-F1 over five roles with spec-level grouping.

## 6. Cost and fidelity measurements
Latency: wall-clock median/p95/p99 over >=1000 runs after warm-up for feature extraction, ONNX inference and end-to-end, per result-set size (10, 100, 1000, 10000 rows), single thread, machine described. Memory: peak RSS delta. Size: bytes of ONNX/model files and wheels/packages. Parity: >=250 golden fixtures, atol = rtol = 1e-6, per runtime. Anomalies: injected-anomaly recovery (precision/recall) and independent numeric recomputation.

## 7. Stopping and exclusions
No outcome-dependent exclusion of items. Items rejected by the contract (out of bounds, lexer errors) are counted and reported, not dropped silently. If human labels contradict the taxonomy definition, the item stays with the human label.

## 8. Reproducibility
Notebooks `research/kaggle/notebooks/01-03`, MANIFEST.json checksums, byte-reproducible ONNX export (fixed graph name, single-thread training; tested), contract and interpretation pins in every report.

## 9. Deviations from protocol (recorded after `prereg-v1`)
**D1 (owner decision, 2026-11-28): no human validation.** Sections 1 and 3 planned a confirmatory evaluation against at least two independent human annotators. The project owner decided that no human validation will be collected. The reference for the reserved 100 items is therefore the **agreement of LLM annotators**, declared as such: pilot Claude, pilot Codex (GPT family), a Claude single pass, and an AI-generated returned workbook of unknown model. They are not independent (two are the same model family, one has unknown identity) and none is human. Consequences, all applied in `tools/run_llm_reference.py`:
- truth = plurality label over the four annotators (unique top label required; ties are listed and excluded, never guessed); per-annotator scores are also reported;
- provenance `llm_reference`, `confirmatory: false` in every output; nothing from this tier is called human or confirmatory, and the `human` tier and `tools/run_confirmatory.py` remain available if human labels are ever collected;
- the statistical procedure of Section 5 (macro-F1 over classes with >=5 items, 2000-resample paired cluster bootstrap over databases, all pairwise differences, always-`table` baseline) is unchanged;
- hypotheses H1 and H4 are therefore tested only against LLM agreement; the paper states that they are not tested against human judgement.
