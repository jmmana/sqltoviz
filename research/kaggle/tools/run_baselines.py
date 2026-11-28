"""Rule / model / LLM baselines on the NON-human tiers, each report labelled with its provenance (#93, #94).
Usage: run_baselines.py synthetic [--seeds 0 1 2] [--per-class 400]   held-out schemas, synthetic labels (exploratory)
       run_baselines.py llm-agreement                                 the two blind LLM runs against each other (LLM-vs-LLM, not accuracy)
       run_baselines.py llm-items PILOT_ITEMS_JSONL                   synthetic-trained systems vs LLM-consensus labels on the 200 non-reserved items
Writes reports/baselines_<tier>.json. Human labels are never read here: use run_confirmatory.py for the confirmatory path."""
import argparse, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import confirmatory as C, llm_baseline as B, splits as S, synthgen as G, annotations as A

here = os.path.join(os.path.dirname(__file__), "..")
ap = argparse.ArgumentParser(); ap.add_argument("tier", choices=["synthetic", "llm-agreement", "llm-items"]); ap.add_argument("items", nargs="?")
ap.add_argument("--seeds", type=int, nargs="*", default=[0, 1, 2]); ap.add_argument("--per-class", type=int, default=400); ap.add_argument("--out")
a = ap.parse_args()

if a.tier == "synthetic":
    items = G.generate(a.per_class, seed=20261127)
    runs = []
    for sd in a.seeds:
        assign = S.grouped_stratified_split(items, group=lambda x: x["db_id"], seed=sd)
        tr = [i for i in items if assign[i["item_id"]] == "train"]; te = [i for i in items if assign[i["item_id"]] == "test"]
        rep = C.analyze(tr, te, {i["item_id"]: {"label": i["label"]} for i in te}, C.SYNTHETIC, seed=sd)
        rep["split_seed"] = sd; runs.append(rep)
    report = {"provenance": C.SYNTHETIC, "confirmatory": False, "banner": C.BANNER[C.SYNTHETIC], "per_class": a.per_class, "runs": runs}
elif a.tier == "llm-agreement":
    raw = {n: [json.loads(l) for l in open(f"{here}/annotations/raw/{n}.jsonl")] for n in ("claude-sonnet-5-5", "gpt-codex")}
    labs = {}
    for l in open(f"{here}/annotations/pilot_llm_labels.jsonl"):
        d = json.loads(l)
        if not d["reserved_for_human_validation"]:
            labs[d["item_id"]] = d
    out = {}
    for pred, ref in (("claude-sonnet-5-5", "codex_primary"), ("gpt-codex", "claude_primary")):
        recs = [B.RunRecord(d["item_id"], pred, "blind-pilot-guidelines", "n/a", json.dumps(d), B.parse_response(json.dumps(d))) for d in raw[pred] if d["item_id"] in labs]
        truth = {i: {"label": labs[i][ref], "acceptable": labs[i][ref.replace("primary", "acceptable")]} for i in labs}
        out[f"{pred}_vs_other_llm"] = B.score(recs, truth, {i: labs[i]["db_id"] for i in labs}, reps=1000)
    report = {"provenance": C.LLM, "confirmatory": False, "banner": C.BANNER[C.LLM], "n_free_items": len(labs),
              "note": "each run scored against the OTHER LLM's labels; this is inter-LLM agreement, not accuracy; reserved items excluded", "runs": out}
else:
    items = {json.loads(l)["item_id"]: json.loads(l) for l in open(a.items)}
    reserve = set(json.load(open(f"{here}/annotations/human_validation_reserve_ids.json")))
    truth = {}
    for l in open(f"{here}/annotations/pilot_llm_labels.jsonl"):
        d = json.loads(l)
        if d["label"] and d["item_id"] in items and d["item_id"] not in reserve:
            truth[d["item_id"]] = {"label": d["label"], "acceptable": d["acceptable"]}
    free = [it for i, it in items.items() if i not in reserve]
    report = C.analyze(G.generate(a.per_class, seed=20261127), free, truth, C.LLM)
out = a.out or f"{here}/reports/baselines_{a.tier.replace('-', '_')}.json"
C.write_report(report, out); print("wrote", out)
