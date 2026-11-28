# Release-candidate integration tests (#102)

`scripts/release/rc_integration.sh` + `.github/workflows/rc-integration.yml`.

1. `build`: `python -m build` (wheel + sdist), `npm pack`, `dotnet pack` for `SqlToViz` and `SqlToViz.Onnx`.
2. `test <artifacts> python|node|dotnet`: creates a clean venv / npm project / console project in a temp dir, installs **only the packed artifact** (plus the optional runtime: onnxruntime+numpy, onnxruntime-node 1.31.1; .NET restores the .nupkg files from a local feed), and runs every case of `parity/golden_v1.json` (308: 295 accepted, 13 rejected) through the public API.
3. `scripts/release/rc/compare.py` checks classes, constraint flag, eligibility, roles, chart and role scores (atol/rtol from the golden file), rejections, `model_status == experimental`, and (Python/npm) that the installed model SHA-256 equals the manifest.

CI matrix: Python 3.10/3.12/3.13, Node 20/22, .NET net8.0/net10.0. Local run (macOS, Python 3.12, Node 24, .NET net10.0): all three 295 accepted / 13 rejected / 0 failures.

## Limits
- Tests the artifacts built from the candidate commit; any later change to package inputs needs a re-run at the final release commit.
- Linux only; nothing is published, signed or installed from a registry (the packages are not on any registry). Transitive runtime packages (onnxruntime etc.) come from the public registries at test time.
- .NET output does not re-hash the embedded models (the engine enforces the manifest SHA-256 on load); the sdist is built but not separately installed.
- Golden fixtures and models are the experimental candidates; passing proves cross-SDK agreement with the reference, not recommendation quality.
