# Synthetic SQL without label leakage (E01-07, #25)

Generator: `sqltoviz_data/synthgen.py`; audit: `sqltoviz_data/leakage.py`; CLI: `tools/generate_synthetic.py OUT N SEED`. License namespace: `apache-2.0` (own code, no third-party text).

## Construction
- **Label from the result data, not the SQL.** Each of the 10 base classes has a data generator with non-overlapping regimes (e.g. donut 2-5 positive categories; bar 6-15; horizontal_bar 8-25 with long labels; stacked_bar 3-10 × 2-4 series; heatmap fully crossed ≥6×6; kpi single row; area non-negative zero-baseline vs line shifted/sign-changing; scatter ≥30 paired measures; table 6-10 mixed columns). Ambiguous zones are excluded; `acceptable` lists the lenient alternatives (bar↔horizontal_bar, donut→bar, line↔area).
- **Class-agnostic schemas:** 300 schema families (table/column names from shared vocabularies); every schema can emit every class, so grouped splits by `db_id` are leak-free (χ² independence test in the unit tests).
- **Templates per result shape, independent of the class** (bar/horizontal_bar/donut share theirs; line/area; stacked_bar/heatmap). Sortedness is identical across the three category classes, so `ORDER BY` carries no label information.
- **No chart vocabulary** (bar, pie, line, area, chart, kpi, …) in SQL, identifiers or aliases (asserted).
- Every item passes the frozen SqlVizSpec-v1.0.0 extractor (no rejections).

## Measured leakage audit (seed 20261127, 2000 per class = 20 000 items, 5-fold GroupKFold by schema, random forest)
Some dependence is structural: SQL fixes the result *shape*, which narrows the label set. With perfect shape knowledge and uniform guessing inside each shape, best accuracy is the **structural ceiling = 0.60**.

| View (input to classifier) | Accuracy | Macro-F1 | Within-shape accuracy vs chance |
|---|---|---|---|
| 16 SQL features (frozen contract) | 0.570 | 0.570 | cat 0.325/0.333, time 0.482/0.500, two-nominal 0.487/0.500 |
| SQL token bag | 0.589 | 0.586 | 0.333/0.333, 0.491/0.500, 0.507/0.500 |
| Column/table names only | 0.509 | 0.504 | 0.339/0.333, 0.497/0.500, 0.503/0.500 |
| *(reference)* 16 global data features | 0.852 | 0.850 | cat 0.857, **time 0.472 (line vs area not separable by table-level features)**, two-nominal 1.000 |

Reading: SQL-only and name-only models stay at or below the structural ceiling and are at chance inside every shape, i.e. no class-specific SQL signal was found by these probes. Data features are informative, as intended. Full JSON: `reports/leakage_audit_seed20261127.json` (dataset SHA256 `a6fffdcc…2384b`).

## Limitations (to carry into the paper)
1. **Labels encode our generation convention**, not human preference; metrics on synthetic data measure agreement with these rules and must never be presented as real-world accuracy. Real-data evaluation requires the annotations of #24.
2. The probes are random forests on three SQL/name views; absence of detected leakage is not a proof. Other probes (e.g. neural text models) were not run.
3. Line vs area differ only through column-level statistics (baseline/sign); the table-level view cannot separate them, so role/column features matter for that pair.
4. Data are cleaner and more regular than real result sets; domain shift is expected.
Tests: `pytest tests/test_synthgen.py` (13 tests incl. the leakage ceiling assertions).
