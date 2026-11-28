# Preliminary experiments and pilot annotation (E01, #24 #27 #28)

Everything below is **preliminary**, produced 2026-11-27 with fixed defaults (no hyper-parameter tuning), contract **SqlVizSpec-v1.0.0** (SHA256 `d14d140b9118c0b535d4e504af7f16546f47d56ac8f1692c2ab62615686e5864`, verified at load and recorded in every JSON under `reports/`). The nine ambiguous contract readings (FEATURE_INTERPRETATIONS.md) are still under review by the contract owner; if any changes, all numbers here must be regenerated.

## Label provenance (kept separate, never merged)
| Source | Where | What it is |
|---|---|---|
| synthetic | `sqltoviz_data/synthgen.py`, 20 000 items (seed 20261127, SHA256 `a6fffdcc…2384b`) | label by construction from data regimes (SYNTHETIC_DATA.md) |
| llm | `annotations/raw/*.jsonl`, `annotations/pilot_llm_labels.jsonl` | two LLM annotators of different families |
| human | none yet | 100 items reserved: `annotations/human_validation_reserve_ids.json` |

## Pilot annotation (300 Spider train queries, blind pack SHA256 `81191650…4750`)
Annotators: Claude Sonnet 5.5 (fresh subagent) and GPT via the Codex runtime, each given only `GUIDELINES_BLIND_PILOT.md` and the pack (SQL, columns, ≤20 rows); instructed not to see synthetic labels, model outputs or each other's work, and to judge each item without auto-labelling scripts (compliance is instruction-based and cannot be audited beyond that). Multiple valid charts allowed (`acceptable`) plus a preferred `primary`.
- Percent agreement on primary: **92.7 %**; Cohen's κ **0.844** (reports/pilot_agreement.json). Primary of A is within B's acceptable set 99.7 %, B in A 96.7 %; acceptable sets always intersect; mean Jaccard 0.79.
- Class use: Claude table 216 / kpi 58 / bar 22 / horizontal_bar 4; GPT table 202 / kpi 64 / bar 17 / horizontal_bar 15 / line 1 / scatter 1. Disagreements (22): bar↔horizontal_bar 6+, table↔kpi 6, table↔horizontal_bar 5, table→bar 2, others 3.
- **This is agreement between two LLMs, not human consensus.** 100 items (stratified by consensus class + a disagreement stratum, seed 20261127) are reserved for human validation and excluded from every LLM-label experiment below (200 free items; 185 with LLM consensus).
- **Finding:** real Spider queries are overwhelmingly detail/lookup results: ≈70 % `table`, no stacked_bar/area/donut/heatmap at all. The pilot cannot evaluate those classes; they remain supported only by synthetic labels until a chart-rich real source is annotated.

## E1: synthetic → synthetic, held-out schemas (3 split seeds, 14 000 train / ≈3 000 test items)
Measures: agreement with the generator's own convention on unseen schemas. **Not** real-world accuracy.
| System | macro-F1 (mean ± sd) | accuracy | semantic violation rate |
|---|---|---|---|
| rules only | 0.913 ± 0.001 | 0.919 | 0 |
| SQL features only | 0.570 ± 0.004 | 0.573 | 0.085 |
| data features only | 0.855 ± 0.004 | 0.855 | 0.021 |
| hybrid SQL+data (32 features, contract input) | 0.855 ± 0.001 | 0.855 | 0.022 |
| hybrid + semantic constraints | 0.876 ± 0.002 | 0.877 | 0 |
Reading: (i) the rules were written by the same person who wrote the generator (thresholds pre-registered in rules.py before any run, but aligned with the taxonomy regimes), so their lead partly reflects a shared convention; (ii) the 32 table-level features **cannot separate bar vs horizontal_bar (needs label length) or line vs area (needs sign/baseline)** — (split seed 0) hybrid F1 for those pairs is 0.73/0.82 and 0.46/0.53 while rules, which read column features, reach 1.0/1.0 and 0.58/0.79; this is a structural limit of the contract's chart-model input, reported to the contract owner; (iii) constraints remove violations and recover part of the line/area gap.

## E2: synthetic-trained → real Spider queries labelled by LLMs (200 free items)
Measures: agreement of systems trained on synthetic data with LLM judgements on real queries (transfer). Majority-class baseline (always `table`): 0.72 (Claude labels), 0.675 (GPT labels), 0.724 (consensus, n=185).
| System | acc vs consensus | macro-F1 (4 present classes) | semantic violation | table fallback |
|---|---|---|---|---|
| rules only | 0.903 | 0.647 | 0 | 0.69 |
| SQL only | 0.568 | 0.482 | 0.41 | 0.36 |
| data only | 0.232 | 0.211 | 0.67 | 0.02 |
| hybrid | 0.605 | 0.505 | 0.31 | 0.39 |
| hybrid + constraints | 0.914 | 0.650 | 0 | 0.70 |
(Per-annotator results in reports/pilot_e2_e3.json: Claude labels 0.865/0.870 for rules/hybrid+constraints, GPT labels 0.85/0.86.)
Reading: models trained on synthetic data **over-recommend charts on real detail-style queries** (violation 0.31–0.67); the hard constraints fix that, and constrained hybrid ≈ rules ≈ "mostly answer table", only slightly above the 0.724 majority baseline. These numbers do not show that charts are recommended well; only 4 classes occur and `table` dominates.

## E3: grouped 5-fold CV inside LLM-consensus labels (185 items; table 134, kpi 39, bar 10, horizontal_bar 2)
Preliminary only: training on 148 items per fold. Accuracy/macro-F1 (cluster-bootstrap 95 % CI over databases): rules 0.903/0.647 [0.47,0.74]; SQL-only 0.914/0.655; data-only 0.930/0.759 [0.61,0.90]; hybrid 0.946/0.697 [0.64,0.73]; hybrid+constraints 0.957/0.706 [0.66,0.74]; majority 0.724. With 2 horizontal_bar items the per-class F1 is meaningless; differences between systems are inside the confidence intervals. No ranking claim is made.

## Reproduce
`tools/generate_synthetic.py`, `tools/run_e1.py`, `tools/build_pilot_items.py`, `tools/run_pilot.py` (see each docstring). Unit tests: `pytest tests` (rules, experiment protocol, pilot statistics).
## Limitations
Fixed RF defaults; one random seed for E2/E3; Spider-only real data (no chart-rich real source); LLM labels unvalidated by humans; contract readings unconfirmed; ONNX/SDK parity not yet measured.


## Full notebook run (commit-pinned, byte-reproducible; 2026-11-27)
Executed `notebooks/01-03` in `full` mode on Spider (train+dev) and BIRD dev, after the contract owner confirmed the nine interpretations (documents pinned in every report; contract SHA256 unchanged). Reports: `reports/full_run/`.
- **Dataset (nb 01):** 9,253 executable gold queries (Spider train 6,743, Spider dev 985, BIRD dev 1,525; 7 BIRD timeouts, 2 out of contract) -> 5,781 after within-database near-duplicate removal; grouped split train 4,050 / val 864 / test 867 items over 117 / 26 / 27 databases (audit passes); 20,000 synthetic items (SHA256 `a6fffdcc…`, identical to the earlier session = deterministic); leakage audit unchanged (SQL-only 0.570, names-only 0.509, ceiling 0.60).
- **E1 (3 split seeds)** reproduces the table above to three decimals (rules 0.913, SQL-only 0.570, data-only 0.855, hybrid 0.855, hybrid+constraints 0.876) with single-threaded training.
- **Leave-one-group-out ablation (hybrid, synthetic):** full 0.854; removing data_size -0.019, data_cardinality -0.002, sql_size +0.003, sql_clauses 0.000, sql_semantic 0.000, data_types 0.000 -> the 32 features are highly redundant on this synthetic data (exploratory; RQ3).
- **E2 (n = 131 LLM-consensus items that survive dedup; always-`table` baseline 0.725):** rules 0.885 acc / 0.639 macro-F1; SQL-only 0.573 / 0.494; data-only 0.229 / 0.221; hybrid 0.588 / 0.492; hybrid + constraints **0.908 / 0.644**, violations 0.32 -> 0, table fallback 0.695. Smaller than the pilot's n = 185 because dedup removes near-duplicate pilot queries. Still LLM labels, still not human.
- **ONNX (nb 03):** chart model 5,772,489 bytes; vs scikit-learn on 2,942 held-out items max |diff| 2.6e-7 (tolerance 1e-6), argmax equal 100 %; export is **byte-identical** across independent re-trainings (SHA256 `578f836f…`). 288 golden fixtures (38 hand-crafted incl. 11 rejections, 250 synthetic = 25 per class) verified with 0 failures.
- **Cost (Python reference, Apple M4 Pro, 1 thread, `tools/benchmark.py`):** end-to-end median 0.23 ms (10 rows), 0.62 ms (100), 4.75 ms (1,000), 45.3 ms (10,000); p95 0.30 / 0.73 / 5.12 / 47.95 ms; ONNX inference alone 0.008-0.072 ms; peak process RSS about 280 MB (dominated by library imports; growth during runs < 1 MB); chart model 5.77 MB, role model 0.31 MB. Other SDKs not measured.

## Reproducibility check after the cross-runtime numeric changes (2026-11-27)
Notebooks 01-03 were re-run in `full` mode on the final development code (explicit left-to-right sums, exact constant-column test, integer row-count recovery in the constraints, `n_jobs=1` training). **E1 (3 seeds), the ablation and E2 (n = 131) reproduce the numbers above exactly, and the candidate chart ONNX keeps SHA256 `578f836f…54ce`** (byte-identical), although a handful of float32 feature values changed in the last bit. A kernel death seen in two intermediate re-runs was caused by `pipeline.load_features` decompressing the `.npz` once per item (fixed in PR #176), not by the experiments.
