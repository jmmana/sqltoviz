# SqlVizSpec-v1.0.0 reference extractor: validation and interpretation notes

Implementation: `sqltoviz_data/features.py`, pinned to contract SHA256 `d14d140b9118c0b535d4e504af7f16546f47d56ac8f1692c2ab62615686e5864` (checked at load; any other bytes are rejected). Written from the contract text only.

## Independent validation (2026-11-27)
| Check | Reference | Result |
|---|---|---|
| Hand-derived vector (token count, aggregates, CV, range, type-7 IQR, MAD, monotonicity, entropy, temporal step 1/9) | analytic | pass |
| 40 random quantitative columns: CV, skewness, excess kurtosis, ratios, range, IQR, MAD, monotonicity | numpy + scipy | pass (rel 2e-6) |
| Lexical SQL features on 2568 gold queries (Spider dev + BIRD dev) | sqlglot AST | join_count, has_group_by, has_order_by, has_limit, has_distinct, has_having, has_window: 100% agreement; subquery_cte_count 99.92% (2 mismatches: `EXISTS (SELECT …)`, which sqlglot models as `Exists`, not `Subquery`; the contract counts SELECT after "(") |
| 150 fuzzed inputs | invariants | all outputs finite, in declared range, float32, deterministic |
| Real end-to-end extraction (SQL + executed result) | Spider dev, BIRD dev | 2510 ok, 0 rejections; 51 results empty/over 100000 rows (contract fallback to table); 7 BIRD queries time out |

`tests/test_features.py` (57 tests), `tools/crosscheck_sqlglot.py`, `tools/extract_corpus_check.py`. Not validated here: cross-language parity (SDK work), ONNX parity, and statistics on the *contract's* intended semantics beyond these references.

## Readings of ambiguous contract text (please confirm, they affect cross-SDK parity)
1. `normalized_limit`: first outer `LIMIT`/`TOP` followed by an integer literal; `TOP (n)`, `LIMIT ALL`, parameters → 1; MySQL `LIMIT a, b` uses `a`.
2. `aggregate_count`: aggregates inside the union of all SELECT projection spans, each token counted once (a subquery inside a projection is not double counted).
3. `calculated_projection_ratio`: denominator = all outer projection expressions (wildcards included, with no operator); `DISTINCT`/`ALL`/`TOP n` after SELECT are skipped.
4. `crossed_structure`: nominal count = 2 and quantitative count = 1 (temporal/identifier columns may also exist); "all cells nonmissing" is over every column.
5. `mean_nominal_entropy`: nominal columns with K<=1 contribute 0 and stay in the mean.
6. Outer `GROUP BY` resolution uses only the first arm of a set operation; a group item that matches both an output name and a different projected expression is ambiguous (→ 0).
7. RFC3339 requires `T`/`t` separator and explicit offset; leap second `:60` and invalid calendar dates are not temporal.
8. Unbalanced `)` clamps depth at 0 (not rejected); only unclosed quotes/comments/brackets reject.
9. Typed distinctness: `1` and `1.0` equal, booleans distinct from numbers, temporal by UTC seconds; identifier/temporal/quantitative inference needs at least one nonmissing value.
