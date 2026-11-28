# arXiv preparation (E08-10, #98) - nothing is submitted

`tools/prepare_arxiv.py` compiles `manuscript/main.tex` from a clean directory (tectonic), keeps the `.bbl`, builds `arxiv_source.tar.gz` and evaluates readiness gates. It never submits. Run: `python tools/prepare_arxiv.py --out DIR` -> `DIR/readiness_report.json`.

## Current gate status (2026-11-28): NOT READY (one gate: authors)
Declared design (owner, 2026-11-28; PROTOCOL.md D1): **no human validation**. The gates no longer require a human report; they require `reports/llm_reference_reserved100.json` (provenance `llm_reference`, `confirmatory: false`) and a manuscript that states there is no human validation and that the reference is LLM agreement of non-independent annotators. The manuscript also states that on nvBench's human-authored labels the experimental models are not validated and poor in accuracy. All gates pass except `authors_completed`. References: 23/23 verified (`tools/verify_references.py`).

## What must happen before submission (owner/authors; nothing here submits)
1. Authors and affiliations (the `\thanks` note says they are to be completed).
2. Choose licence and categories (suggested, not chosen: primary cs.DB, cross-list cs.HC/cs.LG).
3. Endorsement if required for the category.
4. Final proofreading, then submission by the authors, manually.
