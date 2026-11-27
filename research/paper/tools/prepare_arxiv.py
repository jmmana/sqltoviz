"""Build an arXiv source bundle and check readiness gates. NEVER submits anything.
Usage: prepare_arxiv.py [--out DIR]
Gates (all must pass for READY): clean compile, .bbl present, no unresolved citations, no TODO markers, all references verified,
human validation report present, no absolute paths, size limit. Today the human-validation and TODO gates are expected to fail."""
import json, os, re, shutil, subprocess, sys, tarfile
from pathlib import Path

here = Path(__file__).resolve().parent.parent
ms = here / "manuscript"
out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else here / "arxiv_build"
shutil.rmtree(out, ignore_errors=True); (out / "src").mkdir(parents=True)
for f in ("main.tex", "references.bib"):
    shutil.copy(ms / f, out / "src" / f)
r = subprocess.run(["tectonic", "main.tex", "--keep-intermediates", "--keep-logs"], cwd=out / "src", capture_output=True, text=True)
tex = (ms / "main.tex").read_text()
log = (out / "src" / "main.log").read_text(errors="ignore") if (out / "src" / "main.log").exists() else ""
refs = json.loads((here / "related_work" / "verification_report.json").read_text())["entries"]
hv = here.parent / "kaggle" / "reports" / "human_validation_report.json"
gates = {
    "compiles_from_clean": r.returncode == 0 and (out / "src" / "main.pdf").exists(),
    "bbl_present": (out / "src" / "main.bbl").exists(),
    "no_unresolved_citations": "Citation" not in log or "undefined" not in log,
    "no_todo_markers": "\\todo{" not in tex.replace("\\newcommand{\\todo}", ""),
    "all_references_verified": all(e["verified"] for e in refs),
    "human_validation_report_present": hv.exists(),
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
rep = {"status": "READY" if ready else "NOT READY", "gates": gates, "bundle": str(bundle), "bundle_bytes": bundle.stat().st_size,
       "suggested_metadata": {"primary_category": "cs.DB (to be confirmed by authors)", "cross_lists": ["cs.HC", "cs.LG"],
                              "license": "author decision (e.g. CC BY 4.0); not chosen automatically",
                              "comments": "draft; preliminary evaluation; code and fixtures in repository"},
       "manual_steps_remaining": ["authors/affiliations", "endorsement if first arXiv submission in the category", "licence choice", "human-validated evaluation and revised abstract/conclusion",
                                  "TypeScript/.NET parity numbers", "final proofreading", "submission itself (never automated here)"]}
(out / "readiness_report.json").write_text(json.dumps(rep, indent=1))
print(json.dumps({"status": rep["status"], "gates": gates}, indent=1))
