# Cross-runtime parity fixtures

`golden_v1.json`: 288 cases for SqlVizSpec-v1.0.0 (38 hand-crafted edge cases including 11 expected rejections, 250 synthetic cases, 25 per base class). Each case holds `sql`, `schema`, `rows` and the expected `table_features[32]`, `column_features[M,28]`, `chart_scores[10]` (candidate chart model) or an expected rejection. Tolerance: atol = rtol = 1e-6 (contract). Reference implementation: `research/kaggle/sqltoviz_data` (verified: 0 failures, max abs diff 0). Fixtures are synthetic/hand-written only and redistributable under Apache-2.0.
**Status:** verified in Python only; TypeScript and .NET SDKs must pass the same file before parity is claimed (SDK epics). `chart_scores` depend on the candidate model; feature parity does not.
