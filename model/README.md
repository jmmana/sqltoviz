# Model artifacts

`candidate/` holds **candidate** ONNX models (not final): `chart_model_candidate.onnx` (table_features[batch,32] -> chart_scores[batch,10], contract class order, trained on 20,000 synthetic items) and `role_model_candidate.onnx` (column_features[M,28] -> role_scores[M,5], trained on 322 columns from expert Vega-Lite specs). Each has a model card with contract version and SHA256, interpretation-document pin, class/role order, verification against scikit-learn, training provenance and limitations; `CHECKSUMS.sha256` lists SHA256 for every file. Exports are byte-reproducible (see EXPERIMENTS.md).

Status: no human validation yet, synthetic-only chart labels, tiny role supervision. Do not describe these as validated recommendations. A final model requires the human-labelled evaluation in `research/paper/PROTOCOL.md`.
