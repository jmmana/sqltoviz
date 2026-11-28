# Registry name availability (#99)

Reproduce with `python scripts/release/check_registry_names.py` (read-only GETs).

Observed on **2026-11-28 01:06 UTC**:

| Registry | Query | Result |
|---|---|---|
| PyPI | `/pypi/sqltoviz/json`, `/pypi/sqltoviz/0.1.0a1/json` | 404, 404 |
| PyPI | look-alikes `sql-to-viz`, `sqltoviz-core` / `sqlviz` | 404 / **200 (exists, unrelated project; different name, not a collision)** |
| npm | `@sqltoviz/core`, `@sqltoviz/core@0.1.0-alpha.1`, unscoped `sqltoviz` | 404, 404, 404 |
| npm | search `scope:sqltoviz` | 200, no packages |
| NuGet | flat-container `sqltoviz`, `sqltoviz.onnx` | 404, 404 |
| NuGet | search `sqltoviz` | 200, no packages |

## What this proves and does not
- Proves: the names were not publicly visible at check time (no existing package that would block first publication).
- Does **not** prove: that the names are reserved, that the `sqltoviz` npm organization/scope exists or is controlled by this project, that trusted publishers (PyPI/NuGet/npm) are configured, or who will own the names. A public lookup cannot show any of this.

## Maintainer checklist (cannot be verified from the repo)
- [ ] PyPI: create/reserve project `sqltoviz` (or pending publisher) and configure trusted publishing for `publish-pypi.yml` / environment `pypi`.
- [ ] npm: confirm control of the `@sqltoviz` scope/org; configure provenance publishing for `publish-npm.yml`.
- [ ] NuGet: reserve ID prefix `SqlToViz` and configure `publish-nuget.yml`.
Until these are ticked, #99 stays open.
