"""Evaluate the five systems on the reserved 100 against the LLM-reference truth (declared design: no human validation).
Usage: run_llm_reference.py RESERVE_ITEMS_JSONL [--out PATH] [--reps N]
RESERVE_ITEMS_JSONL: item_id/db_id/sql/columns/rows of the 100 reserved items (build_pilot_items.py output filtered to
annotations/human_validation_reserve_ids.json; Spider text, CC BY-SA 4.0, never committed).
Writes reports/llm_reference_reserved100.json with provenance llm_reference, confirmatory false."""
import argparse, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import confirmatory as C, llm_reference as L, synthgen as G
here = os.path.join(os.path.dirname(__file__), "..")
ap = argparse.ArgumentParser(); ap.add_argument("items"); ap.add_argument("--out", default=f"{here}/reports/llm_reference_reserved100.json")
ap.add_argument("--reps", type=int, default=C.BOOTSTRAP_REPS); ap.add_argument("--per-class", type=int, default=2000)
a = ap.parse_args()
reserve = set(json.load(open(f"{here}/annotations/human_validation_reserve_ids.json")))
items = [json.loads(l) for l in open(a.items)]
items = [i for i in items if i["item_id"] in reserve]
assert len(items) == 100, len(items)
rep = L.evaluate(items, L.load_annotators(f"{here}"), G.generate(a.per_class, seed=20261127), reps=a.reps)
rep["items_sha256_ids"] = __import__("hashlib").sha256(json.dumps(sorted(reserve)).encode()).hexdigest()
print("wrote", C.write_report(rep, a.out))
