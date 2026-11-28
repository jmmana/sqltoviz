# Publishing reproducible Kaggle artifacts and checksums (E01-12, #30)

`sqltoviz_data/publish.py` stages **two license-separated datasets** from a notebook output directory and verifies every file against `MANIFEST.json` (SHA256) and the pinned contract hash:
- Apache-2.0: synthetic data, features, candidate ONNX + model card, golden parity fixtures, reports.
- CC BY-SA 4.0: features/items derived from Spider/BIRD, LLM pilot labels, `ATTRIBUTION.md`.
Each staged folder gets `CHECKSUMS.sha256`, `PROVENANCE.json` (contract version/SHA256, commit, label provenance) and `dataset-metadata.json`.

Guards (tested): refuses smoke-mode outputs, refuses a model whose card says CANDIDATE, refuses tampered files; uploading is a separate explicit call (`publish.upload`) and creates **private** datasets.

```python
from sqltoviz_data import publish as P
print(P.stage("OUT_DIR", "STAGING_DIR", username="<kaggle-user>", allow_candidate=False))   # dry run: stage only
```
Status (2026-11-28): **published, public.**
- https://www.kaggle.com/datasets/maktub83/sqltoviz-synthetic-model-parity - Apache-2.0 (Kaggle's license field says `other`, the description states Apache-2.0): synthetic data, EXPERIMENTAL candidate ONNX (sha256 `578f836f...5b54ce`), model card, 308 golden parity cases, dataset audit.
- https://www.kaggle.com/datasets/maktub83/sqltoviz-real-derived-ccbysa - CC BY-SA 4.0: Spider/BIRD-derived features and items, grouped splits, LLM pilot labels, ATTRIBUTION.
- Visibility was changed with the Kaggle API (`kaggle datasets metadata --update` with `isPrivate: false`); titles <= 50 chars, subtitles 20-80, keywords must come from Kaggle's tag list.
- Verified after publishing: both datasets downloaded from Kaggle, all 11 files pass `CHECKSUMS.sha256`, `PROVENANCE.json` carries contract SqlVizSpec-v1.0.0 and its SHA256.
- Scope and limits: labels are synthetic or LLM, **no human validation**; the model is a candidate and on the external nvBench benchmark its accuracy is far below an always-bar baseline (research/paper/NVBENCH_EVALUATION.md). nvBench data, the human-validation key and any VizML-derived material are NOT in these datasets.
