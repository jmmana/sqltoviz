# Model metadata and license verification (#101)

Verified by `scripts/release/verify_model_metadata.py` (runs in CI via `.github/workflows/release-checks.yml`). Engineering record, not legal advice.

## What is verified (mechanically)
- `chart_model_candidate.onnx` and `role_model_candidate.onnx` have identical SHA-256 in `model/candidate/`, the Python wheel sources, the npm package and the NuGet `SqlToViz.Onnx` project, and match the model cards and each package `manifest.json`.
- Every manifest and card says `experimental` / `CANDIDATE`; the contract hash matches `spec/sqlvizspec-v1-features.json`.
- `model/candidate/CHECKSUMS.sha256` matches every listed file (now including `LICENSE_METADATA.json`).

## License facts
| Item | Status |
|---|---|
| Project code (SDKs, scripts) | Apache-2.0 (root `LICENSE`) |
| Chart model training data | Synthetic items from our own generator (Apache-2.0); no third-party text |
| Role model training data | 322 columns from 136 vega/vega-lite example specs, BSD-3-Clause (GitHub API `spdx_id` checked 2026-11-27, pinned commit `2e892a15`). Obligation: keep the copyright notice and disclaimer with redistributed derived material |
| Excluded sources | VizML/Plotly (no license, blocked), Spider/BIRD (CC BY-SA 4.0, not used for the bundled weights) |
| **License of the ONNX weights** | **UNDECIDED.** No redistribution license has been chosen. The Apache-2.0 declared on the packages covers the code; whether it should also cover the weights is a maintainer decision |

## Limits
- The BSD-3-Clause notice for the Vega-Lite specs is recorded in `model/candidate/LICENSE_METADATA.json` but is not yet reproduced in `NOTICE`; that is an open item before any non-experimental release.
- The models are experimental candidates (synthetic labels / 322 Vega-Lite columns, no human validation). Nothing here validates their recommendations.
- This issue's license criterion is therefore only partly satisfied: the facts are recorded and checked, the weights license decision remains open.
