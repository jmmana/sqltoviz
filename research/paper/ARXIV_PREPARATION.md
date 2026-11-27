# arXiv preparation (E08-10, #98) - nothing is submitted

`tools/prepare_arxiv.py` compiles `manuscript/main.tex` from a clean directory (tectonic), keeps the `.bbl`, builds `arxiv_source.tar.gz` and evaluates readiness gates. It never submits. Run: `python tools/prepare_arxiv.py --out DIR` -> `DIR/readiness_report.json`.

## Current gate status (2026-11-27): NOT READY
| Gate | Status |
|---|---|
| compiles from a clean directory | pass |
| `.bbl` present (arXiv does not run BibTeX for you) | pass |
| no unresolved citations | pass |
| all references verified against arXiv/Crossref | pass (19/19) |
| no absolute paths, bundle < 10 MB | pass |
| no TODO markers | **fail** (conclusion pending) |
| abstract free of the "no human validation yet" disclaimer | **fail** (intentionally: it is true today) |
| human validation report present (`research/kaggle/reports/human_validation_report.json`) | **fail** |

## What must happen before submission (owner/authors)
1. Collect the human labels for the 100 reserved cases (workbook ready) and run the confirmatory analysis of `PROTOCOL.md`; revise abstract, results and conclusion; remove the draft banner.
2. Measure TypeScript/.NET parity and cost, finish the full-text literature review (`LITERATURE_REVIEW.md` gaps), complete author list and affiliations.
3. Decide the licence and categories (suggested, not chosen: primary cs.DB, cross-list cs.HC/cs.LG); handle endorsement if required.
4. Re-run the gates until READY, proofread, and submit manually.
