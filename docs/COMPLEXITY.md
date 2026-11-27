# Computational complexity of the SqlVizSpec-v1.0.0 engine (#36)

Notation: N rows, M columns (<= 128), L = SQL length in code points, K = distinct values of a column.

| Stage | Cost | Notes |
|---|---|---|
| Lexing + SQL features (16) | O(L) lexing; clause/projection scans are linear in the token count, with nested-clause scans bounded by O(T^2) in the worst case for T tokens (T is small and independent of N) | lexical only, never executes SQL |
| Type resolution | O(N) per column (temporal parse and numeric checks per value) | |
| Global features (16) | O(N M) | distinct counts via hash sets, entropy O(K) per nominal column; crossed-structure test O(N) |
| Column features (28) | O(N log N) per quantitative column | **exact median, MAD and type-7 quantiles sort the column** (two sorts: values and absolute deviations); moments, ratios and monotonicity are O(N) |
| Constraints / rules | O(M) | fixed-size evaluation over the 32 + 28 features |
| ONNX chart model | O(trees x depth) | independent of N (input is 32 floats) |

Total: **O(N M log N + L + T^2)**. The profiler is therefore *not* constant-time (as the contract states), but the model and rule stages are.

## Empirical scaling (benchmarks/results, median feature-extraction time; Apple M4 Pro; see docs/PERFORMANCE.md)
| SDK | 100 rows | 1,000 rows | 10,000 rows | ratio 100->1,000 | ratio 1,000->10,000 |
|---|---|---|---|---|---|
| Python | 0.605 ms | 4.631 ms | 45.29 ms | 7.7x | 9.8x |
| TypeScript (Node) | 0.130 ms | 0.999 ms | 9.50 ms | 7.7x | 9.5x |
| C# (.NET) | 0.290 ms | 1.130 ms | 12.04 ms | 3.9x | 10.7x |
A pure O(N) cost would give 10x per decade, O(N log N) about 13x (1,000->10,000) and O(N^2) 100x; fixed overheads explain the sub-10x ratios at small N. No super-linear blow-up was observed up to the contract limit (100,000 rows was not benchmarked).

## Automated guard
`packages/python/tests/test_complexity.py` and `packages/npm/tests/complexity.test.mjs` fail if a 10x larger input (2,000 -> 20,000 rows) takes more than 40x longer, which catches an accidental quadratic algorithm while staying robust to CI timing noise.
