# Independent supervision for the role model (E01, #28/#29)

The contract's role model maps per-column features to five roles (x_axis, y_axis, color_series, size_or_secondary, ignore_tooltip). Nothing in the Spider/BIRD/TPC sources carries role labels, and roles inferred from SQL (e.g. GROUP BY -> x) would be circular because `is_in_group_by` is itself an input feature. Options measured on 2026-11-27:

| Option | Measured feasibility | Decision |
|---|---|---|
| **nvBench** (README declares MIT; no LICENSE file) | 7,247 visualizations; 5,955 (82 %) execute directly in Spider databases, 1,188 use binning, 104 fail. 5,953 results have 2 columns and 2 have 3; x_name equals the first column in 100 % and y_name the second in 95 %; `classify` (color) appears in 411 items but almost never as an extra result column | Only trivial positional x/y roles; no size/tooltip; not used for training |
| **Vega-Lite example specs** (BSD-3-Clause, expert-authored, pinned commit in `manifests/vega_lite_pin.txt`) | 634 specs; 136 usable (inline data, no transform, simple encodings); 322 columns: y_axis 134, x_axis 119, color_series 40, ignore_tooltip 19, size_or_secondary 10 (408 specs use external data URLs and were not fetched) | **Used** as feasibility supervision |
| Human role annotation of the reserved cases | not collected | Proposed: add a role sheet to the human-validation workbook once chart labels are done |
| Weak labels from SQL structure | circular with input features | Rejected |

## Result (grouped 5-fold CV by spec, `tools/run_roles.py`, `reports/full_run/role_feasibility.json`)
| System | Accuracy | Macro-F1 [95 % cluster-bootstrap CI] |
|---|---|---|
| majority class | 0.416 | 0.118 [0.113, 0.122] |
| positional heuristic (col 0 = x, col 1 = y, else ignore) | 0.562 | 0.317 [0.273, 0.358] |
| random forest on the 28 column features | 0.584 | 0.501 [0.436, 0.561] |
Per-role F1 (RF): x 0.56, y 0.69, color 0.64, size/secondary 0.36 (10 examples), ignore 0.25 (19 examples). A candidate ONNX (`model/candidate/role_model_candidate.onnx`, 306 KB) matches scikit-learn within 1.2e-7.

**Limits:** 322 columns from 136 specs is small and imbalanced; the data are not SQL-aware (context fixed to `SELECT * FROM data`); Vega-Lite fields with aggregates/derived values are not modelled; no human validation. This is evidence that independent supervision is obtainable and that column features carry role signal beyond position, not a deployable role model.
