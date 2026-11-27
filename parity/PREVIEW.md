# Preview parity

28 hand-authored cases: 15 chart/encoding cases and 13 detector cases. Each runtime reads the same JSON and compares against independently specified expected outcomes. The tolerance is 1e-6 for Pearson. This gate validates only the deterministic alpha subset, not the 60-feature extractor or ONNX tensors. It is not the 250 golden-model fixtures required for full SqlVizSpec-v1 parity. CI success must be observed before claiming passing results.
