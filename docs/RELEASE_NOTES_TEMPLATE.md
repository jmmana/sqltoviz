# Release notes template

Copy to the GitHub release body and `CHANGELOG.md`, fill every field, delete unused lines. Nothing in this file is a release.

```markdown
## SqlToViz [TODO: version] ([TODO: YYYY-MM-DD, only after all three registries are verified])

Status: [TODO: alpha | beta | stable]. Models: [TODO: experimental | validated (link to the validation report)].

### Packages
| SDK | Package | Version | Verified install from registry (date, environment) |
|---|---|---|---|
| Python | sqltoviz | [TODO: 0.1.0aN] | [TODO: ] |
| npm | sqltoviz | [TODO: 0.1.0-alpha.N] | [TODO: ] |
| NuGet | SqlToViz, SqlToViz.Onnx (and adapters if released) | [TODO: ] | [TODO: ] |

### Contract
Feature/response contract: SqlVizSpec-[TODO: vX.Y.Z], SHA-256 `[TODO: ...]` (changed: yes/no; migration: [TODO: ]).

### Added / Changed / Fixed
- [TODO: ]

### Breaking changes
- [TODO: none | list and migration steps]

### Models
Bundled model files with SHA-256 and status from `manifest.json`: [TODO: ]. Training data provenance: [TODO: synthetic | LLM | human]. Validation: [TODO: link to report, or "none: experimental"].

### Evidence
- Release-candidate CI run: [TODO: URL]. Parity: [TODO: n golden cases, fuzz cases]. Performance: link to `docs/PERFORMANCE.md` at this commit (hardware stated there).

### Known limitations
- [TODO: carry over every open limitation; never delete "no human validation" while it is true]

### Citation
See `CITATION.cff`.
```

## Pre-release gates (all must pass; record evidence in the release body)

1. CI green on the release commit (all SDKs, parity, docs, release-candidate tests).
2. Version, `CITATION.cff` `version` and `date-released`, `CHANGELOG.md` updated consistently.
3. Each registry workflow run build-only first; publish only with explicit approval; verify install from the registry afterwards (`docs/alpha-release.md`).
4. Claims review: every number traces to `docs/PERFORMANCE.md` or `research/kaggle/EXPERIMENTS.md`; model status wording unchanged unless a validation report exists.
