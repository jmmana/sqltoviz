# Dependency and secret scanning (#83)

Workflow: `.github/workflows/security.yml` (PRs, pushes to development/main, weekly, manual). Updates: `.github/dependabot.yml` (Actions, pip, npm, NuGet; weekly).

## Secret scanning
- `scripts/security/scan_secrets.py`: regex scan of tracked files (private keys, AWS/GitHub/npm/PyPI/NuGet/Slack/Google tokens, quoted credential assignments). Mark reviewed false positives with `secret-scan: allow` on the line.
- gitleaks v8.30.1 (pinned release, SHA-256 verified in the workflow) over the full git history, with redacted output.
- Limits: pattern based, so unknown token formats and low-entropy or split secrets can be missed. GitHub's own secret scanning/push protection is a repository setting and is neither enabled nor verified by this change.

## Dependency audits (fail on high/critical)
| Ecosystem | Command | Gate |
|---|---|---|
| Python | `pip-audit` on an environment with `sqltoviz[onnx]` installed | any known vulnerability (PyPI advisories carry no severity) |
| npm | `npm audit --json` for `packages/npm` and `docs` | high/critical |
| NuGet | `dotnet list package --vulnerable --include-transitive` for the test project (covers both SDK projects) | High/Critical |

`scripts/security/audit.py` applies the gate. The Python SDK has no mandatory dependencies; onnxruntime/numpy are optional extras and are audited via the extra.

## Exceptions
Listed in `.github/security/audit-exceptions.json` with reason and expiry (expired entries fail). Current state: one, `GHSA-587h-7wmj-h5pm` (launch-editor via vite via vitepress, docs build only; dev server never run or deployed). Observed 2026-11-28: packages/npm 0 vulnerabilities; docs 3 (1 high excepted, 2 moderate not blocking); NuGet none; Python none.

## Limits
- Audits only know published advisories; they say nothing about unpublished flaws or malicious packages.
- `site/` and `research/` requirements are not audited here (research tooling is not shipped).
- Repository settings (Dependabot alerts, secret scanning, branch protection, required checks) are not changed by this workflow.
