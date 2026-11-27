# Alpha release runbook

Scope: deterministic preview only, not the trained SqlVizSpec model or full cross-runtime parity. Versions: Python 0.1.0a1; npm and NuGet 0.1.0-alpha.1. All publication workflows default to build-only and require explicit publish=true on main.

- PyPI: pending publisher jmmana/sqltoviz, publish-pypi.yml, pypi.
- npm: @sqltoviz/core, publish-npm.yml, npm. Configure trusted publisher before first publishing attempt; confirm registry ownership and npm CLI OIDC support.
- NuGet: SqlToViz, publish-nuget.yml, nuget. Set repository variable NUGET_USER to the authorized individual NuGet profile name (not email or organization). OIDC login uses temporary credentials; do not store API keys.

Check CI on release commit, run each workflow build-only, then publish explicitly and verify installation from registry in a clean environment. A successful CI run does not establish successful registry publication. Keep alpha separate from stable; no trained model or scientific performance claims.
