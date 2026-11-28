"""Score the two blind LLM annotation runs as LLM-baseline predictions against HUMAN labels (when they exist).
Usage: score_llm_baseline.py   (reads annotations/raw/*.jsonl and annotations/human_labels.jsonl; prints 'pending' until human labels exist)
The LLM runs used GUIDELINES_BLIND_PILOT.md, not the llm_baseline prompt; they are reported as 'blind annotation runs', not as the v1 prompt."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import llm_baseline as B
here = os.path.join(os.path.dirname(__file__), "..")
hp = f"{here}/annotations/human_labels.jsonl"
if not os.path.exists(hp):
    print(json.dumps({"status": "pending", "reason": "no human labels yet (annotations/human_labels.jsonl); LLM-vs-LLM agreement is not accuracy"})); sys.exit(0)
from collections import Counter
hum = [json.loads(l) for l in open(hp)]
votes = {}
for h in hum: votes.setdefault(h["item_id"], []).append(h)
truth = {}
for i, hs in votes.items():
    c = Counter(h["primary"] for h in hs).most_common()
    if len(c) == 1 or c[0][1] > c[1][1]:
        truth[i] = {"label": c[0][0], "acceptable": sorted({a for h in hs for a in h["acceptable"]}), "n_human": len(hs)}
rep = {"human_items": len(votes), "with_majority": len(truth), "runs": {}}
for name in ("claude-sonnet-5-5", "gpt-codex"):
    recs = [B.RunRecord(d["item_id"], name, "blind-pilot-guidelines", "n/a", json.dumps(d), B.parse_response(json.dumps(d))) for d in map(json.loads, open(f"{here}/annotations/raw/{name}.jsonl"))]
    rep["runs"][name] = B.score(recs, truth)
json.dump(rep, open(f"{here}/reports/llm_baseline_vs_human.json", "w"), indent=1); print(json.dumps(rep, indent=1))
