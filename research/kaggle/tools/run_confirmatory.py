"""Confirmatory analysis of PROTOCOL.md on the human-labelled reserve, plus a clearly FAKE dry-run of the same path.
Usage: run_confirmatory.py --dry-run [--out DIR]          synthetic stand-in, random FAKE labels; output files are named FAKE_*
       run_confirmatory.py KEY_CSV RESERVE_ITEMS_JSONL HUMAN_ID=filled.xlsx HUMAN_ID2=filled2.xlsx
RESERVE_ITEMS_JSONL: item_id/db_id/sql/columns/rows of the 100 reserved items (build_pilot_items.py output, filtered).
The real path writes reports/confirmatory_human.json (provenance human, confirmatory true); it refuses fewer than two annotators."""
import argparse, json, os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import confirmatory as C, human_validation as H, synthgen as G

here = os.path.join(os.path.dirname(__file__), "..")
ap = argparse.ArgumentParser(); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--out"); ap.add_argument("rest", nargs="*")
a = ap.parse_args()
if a.dry_run:
    d = a.out or tempfile.mkdtemp(prefix="sqltoviz_FAKE_dryrun_")
    rep = C.fake_dry_run(d)
    p = C.write_report(rep, os.path.join(d, "FAKE_confirmatory_dryrun.json"))
    print(json.dumps({"provenance": rep["provenance"], "banner": rep["banner"], "n_test": rep["n_test"], "written": str(p)}, indent=1)); sys.exit(0)
key, items_path, *pairs = a.rest
if len(pairs) < 2:
    sys.exit("confirmatory analysis needs at least two independent human annotators (PROTOCOL.md section 3)")
rows, problems = [], {}
for p in pairs:
    hid, path = p.split("=", 1)
    anns, problems[hid] = H.ingest(path, key, hid)
    rows += [{"item_id": x.item_id, "primary": x.primary, "acceptable": list(x.acceptable)} for x in anns]
items = [json.loads(l) for l in open(items_path)]
res = C.resolve_truth(rows)
rep = C.analyze(G.generate(2000, seed=20261127), items, res["truth"], C.HUMAN)
rep.update({"annotators": [p.split("=")[0] for p in pairs], "ingest_problems": problems, "unresolved_items_need_adjudication": res["unresolved"],
            "single_annotator_items": res["single_annotator"]})
print("wrote", C.write_report(rep, f"{here}/reports/confirmatory_human.json"))
