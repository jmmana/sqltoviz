# Separating bar/horizontal_bar and line/area without changing the contract (E01/E08, #40 #93 #94)

**Problem (EXPERIMENTS.md E1):** the chart model sees only the 32 table features, which carry no label length or sign/baseline cues, so it cannot separate `bar` from `horizontal_bar` or `line` from `area` (hybrid F1 0.77-0.81/0.72 and 0.49-0.50 before constraints). The frozen contract is **not modified** here.

## Options evaluated (3 split seeds; thresholds chosen on a validation split, scores on a held-out test split of unseen schemas; `tools/run_pair_resolution.py`, `reports/full_run/pair_resolution.json`)
| Variant | Test macro-F1 (mean ± sd) | bar / horizontal_bar F1 | line / area F1 |
|---|---|---|---|
| hybrid, raw argmax | 0.853 ± 0.001 | 0.81 / 0.72 | 0.49 / 0.50 (seed 0) |
| hybrid + hard semantic constraints | 0.872 ± 0.001 | 0.77-0.81 / 0.72 | 0.63-0.65 / 0.56-0.60 |
| **hybrid + constraints + deterministic pair resolver** (existing contract column features) | **0.985 ± 0.001** | 1.00 / 1.00 | 0.92 / 0.93 |
| *study only:* chart model input extended with 3 column aggregates (needs a contract version bump) | 0.992 ± 0.001 | 1.00 / 1.00 | 0.96 / 0.96 |

Resolver (post-model, uses only `mean_string_length`, `negative_ratio`, `normalized_range` from the contract's column features): for a predicted `bar`/`horizontal_bar`, choose `horizontal_bar` iff the longest nominal label mean length >= L (chosen on validation: 0.2, i.e. 10 characters, over a grid 0.2-0.6); for a predicted `line`/`area`, choose `area` iff all quantitative columns are non-negative and the series spans >= R of its mean (`normalized_range`; chosen 0.5 over a grid 0.25-1.5), always subject to the hard eligibility constraints.

## Does the deterministic rule layer solve it? What this does and does not show
- **Yes, within the synthetic convention**: the two pairs are separable from column features already in the contract, so a contract change is **not required** to recover the gap, and the specializer (deterministic, auditable, SDK-portable) is the natural home.
- **This is not evidence about real data.** The synthetic generator defines `horizontal_bar` by long labels and `area` by non-negative zero-baseline series, so thresholds chosen on its validation split necessarily align with it (L=0.2 is the grid minimum, i.e. the boundary may be even lower). Whether people prefer horizontal bars for long labels, or areas for non-negative series, is exactly what the human validation must test; the LLM pilot contains no area and almost no horizontal bars to check.
- The contract-extension variant is only marginally better (+0.007), so a v1.1 change is not justified by these data.

## Recommendation (not applied)
Keep SqlVizSpec-v1.0.0; implement the resolver in the specializer stage as a *configurable, pre-registered rule* with thresholds re-estimated on human labels; report both pairs' per-class F1 in the paper. If human data show the model + resolver cannot reach acceptable F1, revisit extending the chart-model input in a new contract version (owner: E02). Status: study complete; resolver not yet shipped in the SDKs.
