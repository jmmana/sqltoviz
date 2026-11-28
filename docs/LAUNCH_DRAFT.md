# Launch announcement (DRAFT, not published)

Status: draft for the owner to edit. Nothing here has been posted, and no package has been released from this draft. Replace every `<<...>>` marker before use and re-check each number against `docs/PERFORMANCE.md` and `research/kaggle/EXPERIMENTS.md` on the day of release. Do not add claims that are not in those two files.

Pre-publication checklist (all must be true):

- [ ] The three registry releases are verified from a clean environment (`docs/alpha-release.md`); install commands below are real.
- [ ] `CITATION.cff` author list, ORCID and affiliation completed by the owner; `date-released` set.
- [ ] The paper is not described as submitted or accepted (arXiv readiness is NOT READY: see `research/paper/ARXIV_PREPARATION.md`).
- [ ] The words "experimental" and "no human validation" survive every edit and every shortened version.

---

## Title

SqlToViz (alpha): recommend a chart from the SQL query and the rows you already have

## Short version (about 280 characters)

SqlToViz is an open-source alpha that suggests a chart for a SQL query plus its result rows, locally, in Python, TypeScript and .NET. If no chart is safe it falls back to a table. Bundled ONNX models are experimental and not human-validated. <<link>>

## Post

BI tools and Text-to-SQL agents already know the executed query and its result. Picking a chart from that is easy to get wrong: a polished chart can stack unrelated averages or double-count totals.

SqlToViz is an early alpha of a small library for that step. Give it the SQL text and the result rows; it returns a recommended chart class, the reasons, and a list of which chart types are eligible. It does not execute SQL and does not call a hosted service.

What exists today:

- A frozen, versioned feature contract (SqlVizSpec-v1.0.0) and SDKs for Python, TypeScript/Node and .NET that compute the same features; parity is checked on 308 golden fixtures and a differential fuzz test.
- Deterministic semantic rules that reject unsafe charts and fall back to a table.
- Two bundled ONNX models (chart candidate 5.77 MB, role candidate 0.31 MB). They are **experimental candidates**: the chart model is trained on synthetic labels and the role model on 322 Vega-Lite columns. Every result carries `ModelStatus: "experimental"`.
- Local cost on one machine (Apple M4 Pro, single thread): end-to-end median 0.23 / 0.62 / 4.7 ms in Python for 10 / 100 / 1,000 rows; other runtimes and the browser are in `docs/PERFORMANCE.md`. These numbers describe that hardware only.
- Adapters for MudBlazor and ApexCharts (.NET) and a documented Blazor strategy (`docs/BLAZOR.md`).

What we do not know, and do not claim:

- **No human validation yet.** The pilot compares two LLM annotators (Cohen's kappa 0.844 on 300 Spider queries); that is agreement between LLMs, not human preference. 100 items are reserved for human validation and have not been labelled.
- Real queries in the pilot are about 70% `table`; several chart classes are only supported by synthetic labels.
- Against an always-`table` baseline (0.725 on the n = 131 consensus items), the constrained hybrid reached 0.908 accuracy and rules alone 0.885; the difference between systems is inside confidence intervals in the cross-validation, so we make no ranking claim and no claim of superiority over other tools.
- The accompanying paper is a draft and has not been submitted.

Try it / install: <<install commands once the three registries are verified>>. Docs: <<link>>. Source and issues (Apache-2.0): https://github.com/jmmana/sqltoviz

We would value feedback on queries where the recommendation is wrong, and help labelling cases for the human validation set.

## Suggested FAQ answers

- *Does it send my data anywhere?* No: the SDKs run locally; the host application supplies query and rows. SQL is never executed.
- *Is it accurate?* Unknown. The models are experimental; see the limitations above. Treat output as a suggestion.
- *How do I cite it?* Use `CITATION.cff` (the GitHub "Cite this repository" button once the owner has completed the metadata).

## Channel notes (owner decides; nothing scheduled)

Keep the "experimental / no human validation" sentence in any shortened version. Do not post performance numbers without the hardware qualifier.
