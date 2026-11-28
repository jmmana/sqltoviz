# arXiv preparation (E08-10, #98) - nothing is submitted

`tools/prepare_arxiv.py` compiles `manuscript/main.tex` from a clean directory (tectonic), keeps the `.bbl`, builds `arxiv_source.tar.gz` and evaluates readiness gates. It never submits. Run: `python tools/prepare_arxiv.py --out DIR` -> `DIR/readiness_report.json`.

## Current gate status (2026-11-27): NOT READY
`readiness_report.json` lists every failing gate under `blockers` with what is needed. Compilation uses tectonic, or pdflatex + bibtex when tectonic is absent.
| Gate | Status |
|---|---|
| compiles from a clean directory; `.bbl` present; no unresolved citations | pass |
| all references verified against arXiv/Crossref (`tools/verify_references.py`, 23/23) | pass |
| manuscript names the published release 0.1.0-alpha.2 | pass |
| no FAKE dry-run output in `research/kaggle/reports` | pass |
| no absolute paths, bundle < 10 MB | pass |
| no `\pending{...}` placeholders (human-validation table, conclusion) | **fail** |
| human validation report (`reports/human_validation_report.json`) and confirmatory report (`reports/confirmatory_human.json`: provenance human, >=2 annotators) | **fail** |
| abstract free of the "no human-validated evaluation exists yet" disclaimer; no draft banner in the title | **fail** (both are true today) |
| authors and affiliations completed | **fail** (authors' decision) |

## What must happen before submission (owner/authors)
1. Collect the human labels for the 100 reserved cases (workbook ready), then run `research/kaggle/tools/ingest_human_validation.py` and `run_confirmatory.py` (the path is tested with a FAKE stand-in, never tabulated); fill Table `tab:human`, revise abstract, results, conclusion and limitations; remove the draft banner and every `\pending`.
2. Finish the full-text literature review (`LITERATURE_REVIEW.md` gaps); complete author list and affiliations.
3. Decide the licence and categories (suggested, not chosen: primary cs.DB, cross-list cs.HC/cs.LG); handle endorsement if required.
4. Re-run the gates until READY, proofread, and submit manually. Nothing here submits.
