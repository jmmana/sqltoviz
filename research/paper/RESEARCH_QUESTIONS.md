# Research questions and hypotheses (E08-02, #90)

Status legend: **Exploratory-seen** = a preliminary run (synthetic or LLM-labelled, see `research/kaggle/EXPERIMENTS.md`) already informed the hypothesis, so it cannot count as confirmatory; **Open** = no data seen yet. Confirmatory tests use the protocol in `PROTOCOL.md`.

| ID | Question | Hypothesis (falsifiable) | Primary metric | Status |
|---|---|---|---|---|
| RQ1 | Do lexical SQL features and result-set statistics together recommend base chart classes better than either alone? | H1: on held-out databases with independent labels, hybrid macro-F1 exceeds both SQL-only and data-only by a paired-bootstrap 95 % CI that excludes 0 | macro-F1 over classes with human support | Exploratory-seen (synthetic: hybrid ≈ data-only; SQL-only far lower) |
| RQ2 | Do hard semantic constraints reduce unsafe recommendations without hurting agreement? | H2: constrained hybrid has semantic violation rate 0 by construction and macro-F1 not lower than unconstrained by more than 0.02 | violation rate; macro-F1 delta | Exploratory-seen (synthetic and LLM pilot: violations 2-32 % -> 0) |
| RQ3 | Which feature groups matter? | H3: leave-one-group-out drops of macro-F1 are below 0.05 for every group (redundant features) | delta macro-F1 per group | Exploratory-seen (synthetic: max |delta| 0.019) |
| RQ4 | Do models trained on synthetic labels transfer to real queries? | H4: on human labels, synthetic-trained hybrid+constraints beats the always-`table` baseline in macro-F1 | macro-F1, accuracy vs majority | Exploratory-seen (LLM labels only; human pending) |
| RQ5 | Is cross-runtime numerical parity achievable? | H5: features and ONNX scores agree with the reference within atol = rtol = 1e-6 on >=250 golden fixtures in each SDK | max abs diff; pass rate | Partially seen (Python/ONNX: 2.6e-7; TypeScript/.NET open) |
| RQ6 | What is the cost? | H6: end-to-end recommendation for a typical result set (<=1000 rows) takes under 50 ms median on a laptop CPU, model file under 10 MB | median/p95 latency, RSS, bytes | Open (measurement tool: `research/kaggle/tools/benchmark.py`) |
| RQ7 | Can column roles be learned from independent supervision? | H7: role classifier trained on expert Vega-Lite specs beats a positional heuristic in macro-F1 on held-out specs | macro-F1 | Exploratory-seen (0.50 vs 0.32, n = 322 columns) |
| RQ8 | Are statistical insights numerically faithful? | H8: reported anomaly values match independent recomputation within 1e-9 relative error and injected anomalies are recovered above chance | faithfulness error; precision/recall on injected anomalies | Open |

## Non-goals and claims we will not make
No claim of superiority over VizML/DeepEye/Table2Charts/Draco (no comparable data or code run); no claim about human preference until human labels exist; synthetic and LLM agreement is never reported as human validation.


Declared design (2026-11-28, PROTOCOL.md D1): no human validation will be collected. Wherever a question above says "human labels", the evaluation uses the agreement of LLM annotators (`llm_reference`, exploratory, annotators not independent) and no claim about human preference is made.
