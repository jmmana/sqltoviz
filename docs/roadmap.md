# Roadmap

- [E00 — Foundation](https://github.com/jmmana/sqltoviz/issues/1)
- [E01 — Kaggle dataset and training](https://github.com/jmmana/sqltoviz/issues/2)
- [E02 — Statistical engine and SqlVizSpec](https://github.com/jmmana/sqltoviz/issues/3)
- [E03 — Python SDK](https://github.com/jmmana/sqltoviz/issues/4)
- [E04 — TypeScript SDK](https://github.com/jmmana/sqltoviz/issues/5)
- [E05 — C# SDK (.NET 8/10)](https://github.com/jmmana/sqltoviz/issues/6)
- [E06 — Branding, website and playground](https://github.com/jmmana/sqltoviz/issues/7)
- [E07 — CI/CD, security and quality](https://github.com/jmmana/sqltoviz/issues/8)
- [E08 — Research and arXiv](https://github.com/jmmana/sqltoviz/issues/9)
- [E09 — Release and launch](https://github.com/jmmana/sqltoviz/issues/10)

## Acceptance gates / Criterios de aceptación

| Scope / Alcance | Evidence / Evidencia |
| --- | --- |
| Foundation / Fundación | [Architecture decisions](architecture.md), versioned contracts and repository policies |
| SDKs and charts / SDK y gráficos | Reproducible feature tests, input edge cases, explicit chart coverage and package install tests |
| Browser / Navegador | Responsive functional controls, bilingual public copy and a successful live Pages smoke test |
| Alpha / Alfa | [Release runbook](alpha-release.md), CI at the candidate commit, package ownership verification, model distribution metadata when included, and successful clean installs from each registry after release |
| Scientific claims / Afirmaciones científicas | Independently annotated held-out evaluation, at least 250 golden parity cases, latency measurement and stated limitations |

Verify each issue against its own acceptance criteria. Record the PR, test run,
commit, and live endpoint or package version when relevant. Keep release
evidence tied to the exact commit. Scientific claims require the independent
evaluation even when the experimental preview already runs.

Verifica cada issue con sus propios criterios. Registra el PR, la ejecución de
pruebas, el commit y, cuando aplique, la URL publicada o la versión del paquete.
Conserva la evidencia vinculada al commit probado. Las afirmaciones científicas
requieren evaluación independiente aunque la vista previa experimental funcione.
