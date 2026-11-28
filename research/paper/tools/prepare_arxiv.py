"""Build an arXiv source bundle and check readiness gates. NEVER submits anything.
Usage: prepare_arxiv.py [--out DIR]
Gates (all must pass for READY): clean compile, .bbl present, no unresolved citations, no \\pending placeholders, all references verified,
a HUMAN confirmatory report (provenance human, >=2 annotators), no FAKE dry-run output in reports, current release named, authors completed,
no draft banner, no absolute paths, size limit. Today the placeholder, human-validation, banner and author gates are expected to fail.
The output lists each failing gate under "blockers" with what is needed; nothing is ever submitted."""
import json, os, re, shutil, subprocess, sys, tarfile
from pathlib import Path

here = Path(__file__).resolve().parent.parent
ms = here / "manuscript"
out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else here / "arxiv_build"
shutil.rmtree(out, ignore_errors=True); (out / "src").mkdir(parents=True)
for f in ("main.tex", "references.bib"):
    shutil.copy(ms / f, out / "src" / f)
if shutil.which("tectonic"):
    r = subprocess.run(["tectonic", "main.tex", "--keep-intermediates", "--keep-logs"], cwd=out / "src", capture_output=True, text=True)
elif shutil.which("pdflatex") and shutil.which("bibtex"):
    run = lambda *c: subprocess.run(c, cwd=out / "src", capture_output=True, text=True)
    run("pdflatex", "-interaction=nonstopmode", "main.tex"); run("bibtex", "main"); run("pdflatex", "-interaction=nonstopmode", "main.tex")
    r = run("pdflatex", "-interaction=nonstopmode", "main.tex")
else:
    sys.exit("neither tectonic nor pdflatex+bibtex found")
tex = (ms / "main.tex").read_text()
log = (out / "src" / "main.log").read_text(errors="ignore") if (out / "src" / "main.log").exists() else ""
refs = json.loads((here / "related_work" / "verification_report.json").read_text())["entries"]
reports = here.parent / "kaggle" / "reports"
hv = reports / "human_validation_report.json"


def human_confirmatory_ok():
    p = reports / "confirmatory_human.json"
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        return False
    return d.get("provenance") == "human" and d.get("confirmatory") is True and len(d.get("annotators", [])) >= 2


def fake_in_reports():
    bad = []
    for f in reports.rglob("*"):
        if f.is_file() and ("FAKE" in f.name or (f.suffix == ".json" and "FAKE_DRYRUN" in f.read_text(errors="ignore"))):
            bad.append(str(f))
    return bad


body = tex.replace("\\newcommand{\\pending}", "")
gates = {
    "compiles_from_clean": r.returncode == 0 and (out / "src" / "main.pdf").exists(),
    "bbl_present": (out / "src" / "main.bbl").exists(),
    "no_unresolved_citations": "Citation" not in log or "undefined" not in log,
    "no_pending_placeholders": "\\pending{" not in body and "\\todo{" not in body,
    "all_references_verified": all(e["verified"] for e in refs),
    "human_validation_report_present": hv.exists(),
    "human_confirmatory_report_present": human_confirmatory_ok(),
    "no_fake_dryrun_output_in_reports": not fake_in_reports(),
    "names_current_release_0.1.0-alpha.2": "0.1.0-alpha.2" in tex,
    "authors_completed": "to be completed before submission" not in tex,
    "no_draft_banner_in_title": "not yet validated by human annotators" not in tex,
    "no_absolute_paths": not re.search(r"(/Users/|/private/|C:\\\\)", tex),
    "abstract_has_no_pending_disclaimer": "not yet validated" not in tex.lower() and "no human-validated evaluation exists yet" not in tex.lower(),
}
bundle = out / "arxiv_source.tar.gz"
with tarfile.open(bundle, "w:gz") as t:
    for f in ("main.tex", "main.bbl"):
        if (out / "src" / f).exists():
            t.add(out / "src" / f, arcname=f)
gates["bundle_under_10MB"] = bundle.stat().st_size < 10 * 2 ** 20
ready = all(gates.values())
NEEDS = {"no_pending_placeholders": "replace every \\pending{} (human-validation table, conclusion) with real results",
         "human_validation_report_present": "run tools/ingest_human_validation.py on >=2 returned workbooks",
         "human_confirmatory_report_present": "run tools/run_confirmatory.py (real path) -> reports/confirmatory_human.json with provenance human",
         "abstract_has_no_pending_disclaimer": "rewrite abstract once human results exist",
         "no_draft_banner_in_title": "remove the draft subtitle after confirmatory evaluation",
         "authors_completed": "fill author list and affiliations (authors' decision)",
         "no_fake_dryrun_output_in_reports": "delete FAKE dry-run output from research/kaggle/reports",
         "names_current_release_0.1.0-alpha.2": "update the release section to the version actually published",
         "compiles_from_clean": "fix the LaTeX build", "bbl_present": "BibTeX did not produce main.bbl",
         "no_unresolved_citations": "fix undefined citations", "all_references_verified": "re-run verify_references.py",
         "no_absolute_paths": "remove local paths", "bundle_under_10MB": "shrink the bundle"}
blockers = {g: NEEDS.get(g, "see gate") for g, ok in gates.items() if not ok}
rep = {"status": "READY" if ready else "NOT READY", "gates": gates, "blockers": blockers, "bundle": str(bundle), "bundle_bytes": bundle.stat().st_size,
       "suggested_metadata": {"primary_category": "cs.DB (to be confirmed by authors)", "cross_lists": ["cs.HC", "cs.LG"],
                              "license": "author decision (e.g. CC BY 4.0); not chosen automatically",
                              "comments": "draft; preliminary evaluation; code and fixtures in repository"},
       "manual_steps_remaining": ["authors/affiliations", "endorsement if first arXiv submission in the category", "licence choice", "human-validated evaluation and revised abstract/conclusion",
                                  "decide licence and categories (suggested only)", "final proofreading", "submission itself (never automated here)"]}
(out / "readiness_report.json").write_text(json.dumps(rep, indent=1))
print(json.dumps({"status": rep["status"], "gates": gates, "blockers": blockers}, indent=1))
