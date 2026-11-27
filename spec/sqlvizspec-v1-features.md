# SqlVizSpec-v1.0.0 — frozen definition

The normative machine-readable definition is [sqlvizspec-v1-features.json](sqlvizspec-v1-features.json). This freezes the new v1 feature definitions, not a claim of implemented SDK parity. The 60 definitions comprise 32 table features and 28 per-column features; c20/c21 are normalized IQR and MAD (zero-based). SQL features are lexical and must not include chart labels. The two independent classifiers consume table and column tensors respectively; auxiliary encodings are derived only from validated metadata and deterministic rules. No padding: role inference uses dynamic M. Unknown or unsafe chart semantics fail closed to an eligible alternative or table.

Exact median and quantiles require O(N log N) sorting per quantitative column in the reference implementation; profiling is not claimed constant-time. Feature extraction and the 250 cross-runtime fixtures remain implementation tasks. Every incompatible change requires a contract version bump and retraining. Record SHA256 of exact JSON bytes in model metadata and notebooks.

## Verification
Run python3 spec/verify_contract.py to validate structural constraints and print the exact SHA256. This validates the definition only, not statistical implementations or ONNX parity.
