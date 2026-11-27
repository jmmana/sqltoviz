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
Status: tooling and tests complete; **nothing has been uploaded** - publication waits for contract confirmation and the final (non-candidate) model.
