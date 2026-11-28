# nvBench external evaluation (exploratory, not confirmatory)

Provenance: `external_human_authored_nvbench`, `confirmatory: false`. Script: `research/kaggle/tools/eval_nvbench.py`; aggregate output: `research/kaggle/reports/nvbench_eval.json` (contract SqlVizSpec-v1.0.0, SHA256 `d14d140b…5e864`; chart model SHA256 `578f836f…54ce`, role model `171ddf0d…7151e`, both status `experimental`).

## Method
- Data: nvBench `NVBench.json` (7,247 items, human-authored; SHA256 `8c85a9454fe1343074ba915bcbb379f170ab62bb1279b6a7aed23255e6eefbcf`, verified on download) and the Spider SQLite databases nvBench ships (`databases.zip`, SHA256 `a2e22bf6…da3d`, trust-on-first-use: upstream publishes no hash). Both are downloaded locally by the script into a git-ignored directory. **They are never committed or redistributed**: nvBench's license is ambiguous (README says MIT, no LICENSE file, GitHub API `license: null`) and Spider is CC BY-SA 4.0. The repository holds only the script, aggregate metrics and checksums; a test fails if nvBench files are tracked.
- Inputs to the engine: each item's `data_part.sql_part` is executed verbatim in the existing read-only sandbox (`sqltoviz_data/sandbox.py`); the SQL text, column names and rows go to the Python SDK `Engine.default()` (bundled experimental ONNX chart model + rule constraints). A second view (`chart_data`) instead feeds nvBench's own post-binning/grouping data (`vis_obj`) as a long table (x, y, series) with the same SQL text.
- Label mapping (explicit, unknown types are dropped, never guessed): Bar -> bar, Stacked Bar -> stacked_bar, Pie -> donut, Line -> line, Grouping Line -> line, Scatter -> scatter, Grouping Scatter -> scatter.
- Systems: `model_constrained` (shipped behaviour: model scores plus hard semantic constraints), `model_argmax` (raw model argmax), `rules_baseline` (rules only), `always_bar` (majority baseline).
- Metrics: accuracy; macro-F1 over the 5 covered classes (precision counts predictions in any of the 10 classes, so predicting kpi/table/area etc. is an error); per-class F1 and support; top-2 accuracy for the model (top 2 of raw `chart_scores`; rules and always_bar expose no alternatives); 95% percentile CIs from a cluster bootstrap over database (`db_id`, 152 clusters, 2000 resamples, seed 0, same resamples for all systems). Pairwise differences are in the JSON.
- Dropped items: 145 items whose SQL fails in SQLite (e.g. ambiguous column, aggregate misuse in the original nvBench SQL) and 5 rejected by the feature contract; `chart_data` drops the same 5. Counts are in the JSON (`dropped`).

## Results
### View `sql_result` (SQL executed verbatim; headline), all items
| System | Accuracy [95% CI] | Macro-F1 (5 classes) [95% CI] | Top-2 |
|---|---|---|---|
| always_bar | 0.763 [0.730, 0.793] | 0.173 [0.169, 0.177] | n/a |
| model_argmax | 0.286 [0.223, 0.371] | 0.342 [0.286, 0.389] | 0.383 |
| model_constrained | 0.249 [0.180, 0.345] | 0.220 [0.168, 0.286] | 0.380 |
| rules_baseline | 0.275 [0.209, 0.358] | 0.159 [0.137, 0.186] | n/a |

Support: bar 5418, donut 513, line 430, scatter 378, stacked_bar 358 (n=7097). Per-class F1: model_argmax: bar 0.37, donut 0.27, line 0.03, scatter 0.57, stacked_bar 0.47; model_constrained: bar 0.35, donut 0.27, line 0.04, scatter 0.44, stacked_bar 0.00; rules_baseline: bar 0.42, donut 0.27, line 0.00, scatter 0.11, stacked_bar 0.00

### View `sql_result`, excluding the 1,147 items that use nvBench binning (the SQL lacks that step)
| System | Accuracy [95% CI] | Macro-F1 (5 classes) [95% CI] | Top-2 |
|---|---|---|---|
| always_bar | 0.769 [0.743, 0.797] | 0.174 [0.170, 0.177] | n/a |
| model_argmax | 0.341 [0.282, 0.421] | 0.379 [0.323, 0.430] | 0.456 |
| model_constrained | 0.297 [0.225, 0.391] | 0.241 [0.185, 0.315] | 0.453 |
| rules_baseline | 0.328 [0.263, 0.406] | 0.172 [0.150, 0.196] | n/a |

Support: bar 4575, donut 513, line 207, scatter 378, stacked_bar 277 (n=5950). Per-class F1: model_argmax: bar 0.42, donut 0.28, line 0.04, scatter 0.59, stacked_bar 0.57; model_constrained: bar 0.40, donut 0.28, line 0.07, scatter 0.45, stacked_bar 0.00; rules_baseline: bar 0.47, donut 0.28, line 0.00, scatter 0.11, stacked_bar 0.00

### View `chart_data` (nvBench's own chart data), all items
| System | Accuracy [95% CI] | Macro-F1 (5 classes) [95% CI] | Top-2 |
|---|---|---|---|
| always_bar | 0.762 [0.729, 0.792] | 0.173 [0.169, 0.177] | n/a |
| model_argmax | 0.378 [0.337, 0.432] | 0.432 [0.392, 0.488] | 0.462 |
| model_constrained | 0.354 [0.303, 0.421] | 0.409 [0.352, 0.480] | 0.459 |
| rules_baseline | 0.376 [0.326, 0.439] | 0.309 [0.266, 0.363] | n/a |

Support: bar 5518, donut 520, line 452, scatter 393, stacked_bar 359 (n=7242). Per-class F1: model_argmax: bar 0.47, donut 0.26, line 0.18, scatter 0.53, stacked_bar 0.72; model_constrained: bar 0.46, donut 0.26, line 0.25, scatter 0.43, stacked_bar 0.65; rules_baseline: bar 0.52, donut 0.26, line 0.00, scatter 0.13, stacked_bar 0.63

## Caveats (must accompany any citation of these numbers)
1. **Coverage.** nvBench covers only 5 of our 10 base classes (bar, stacked_bar, donut/pie, line, scatter). kpi, horizontal_bar, area, heatmap and table have no human source here, so nothing is said about them.
2. **Imbalance.** 76% of the items are Bar. Always-bar reaches high accuracy and a very low macro-F1 (~0.17); accuracy alone is misleading and macro-F1 is the primary figure.
3. **Label semantics.** The label is the chart requested in the natural-language question, not the best chart for the data. Disagreement with it is not necessarily an error; our model may also be asked for a different task than the one nvBench encodes.
4. **Domain.** Spider tables are small and clean; results do not transfer to messy real data. Many nvBench queries are answerable only with the request text, which the engine never sees.
5. **Stacked bar / grouping.** In the `sql_result` view the series column is often absent from the SELECT (nvBench groups by it), so the engine cannot know a series exists; `chart_data` adds it back. Binned line items lose their binning in `sql_result`.
6. Exploratory only: not preregistered as confirmatory, single run, no tuning on nvBench.

## Interpretation (honest)
The experimental candidate models are **not validated** by this evaluation and the numbers are poor in absolute terms. On the verbatim-SQL view the shipped (constrained) model reaches accuracy 0.249 against 0.763 for the always-bar baseline, i.e. much lower accuracy than predicting the majority class; its macro-F1 (0.220, CI 0.168-0.286) is above always-bar (0.173) and the rules baseline (0.159), but the model CIs overlap the always-bar value at the lower end. The raw argmax (macro-F1 0.342) is better than the constrained choice here, and the hard constraints cost accuracy, notably they eliminate stacked_bar (F1 0.00) because stacked-bar eligibility needs a series dimension that these SQL results do not expose; with the series restored (`chart_data`) constrained macro-F1 rises to 0.409. The model over-predicts donut and table and rarely predicts line, consistent with having been trained only on synthetic labels. Top-2 accuracy (about 0.38 to 0.46) is below the always-bar accuracy as well. Paired bootstrap differences in macro-F1 favour the models over the rules baseline (excludes zero), which is the only comparison supported here. The models remain EXPERIMENTAL candidates; this result argues for training/annotation on real, human-labelled data rather than for any quality claim.
