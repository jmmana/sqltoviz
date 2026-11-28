# Release notes template

Copy to the GitHub release body and `CHANGELOG.md`, fill every field, delete unused lines. Nothing in this file is a release.

```markdown
## SqlToViz <<version>> (<<YYYY-MM-DD, only after all three registries are verified>>)

Status: <<alpha | beta | stable>>. Models: <<experimental | validated (link to the validation report)>>.

### Packages
| SDK | Package | Version | Verified install from registry (date, environment) |
|---|---|---|---|
| Python | sqltoviz | <<0.1.0aN>> | <<>> |
| npm | @sqltoviz/core | <<0.1.0-alpha.N>> | <<>> |
| NuGet | SqlToViz, SqlToViz.Onnx (and adapters if released) | <<>> | <<>> |

### Contract
Feature/response contract: SqlVizSpec-<<vX.Y.Z>>, SHA-256 `<<...>>` (changed: yes/no; migration: <<>>).

### Added / Changed / Fixed
- <<>>

### Breaking changes
- <<none | list and migration steps>>

### Models
Bundled model files with SHA-256 and status from `manifest.json`: <<>>. Training data provenance: <<synthetic | LLM | human>>. Validation: <<link to report, or "none: experimental">>.

### Evidence
- Release-candidate CI run: <<URL>>. Parity: <<n golden cases, fuzz cases>>. Performance: link to `docs/PERFORMANCE.md` at this commit (hardware stated there).

### Known limitations
- <<carry over every open limitation; never delete "no human validation" while it is true>>

### Citation
See `CITATION.cff`.
```

## Pre-release gates (all must pass; record evidence in the release body)

1. CI green on the release commit (all SDKs, parity, docs, release-candidate tests).
2. Version, `CITATION.cff` `version` and `date-released`, `CHANGELOG.md` updated consistently.
3. Each registry workflow run build-only first; publish only with explicit approval; verify install from the registry afterwards (`docs/alpha-release.md`).
4. Claims review: every number traces to `docs/PERFORMANCE.md` or `research/kaggle/EXPERIMENTS.md`; model status wording unchanged unless a validation report exists.
