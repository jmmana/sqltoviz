"""Ingest returned human workbooks and compare with LLM labels (human labels stay a separate source).
Usage: ingest_human_validation.py KEY_CSV HUMAN_ID=workbook.xlsx [HUMAN_ID2=workbook2.xlsx ...]
Writes annotations/human_labels.jsonl and reports/human_validation_report.json."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import annotations as A, human_validation as H

key, *pairs = sys.argv[1:]
here = os.path.join(os.path.dirname(__file__), "..")
humans, problems = {}, {}
for p in pairs:
    hid, path = p.split("=", 1)
    humans[hid], problems[hid] = H.ingest(path, key, hid)
llm = {}
for l in open(f"{here}/annotations/pilot_llm_labels.jsonl"):
    d = json.loads(l); llm[d["item_id"]] = d
report = {"annotators": {h: len(a) for h, a in humans.items()}, "problems": {h: p for h, p in problems.items()},
          "label_source": "human (separate from llm and synthetic)", "vs_llm": {}}
with open(f"{here}/annotations/human_labels.jsonl", "w") as f:
    for h, anns in humans.items():
        for a in anns:
            f.write(json.dumps({"item_id": a.item_id, "annotator_id": h, "label_source": "human", "primary": a.primary,
                                "acceptable": list(a.acceptable), "confidence": a.confidence, "observations": a.rationale}) + "\n")
for h, anns in humans.items():
    for src in ("claude_primary", "codex_primary"):
        x = [(a.primary, llm[a.item_id][src]) for a in anns if a.item_id in llm]
        if x:
            report["vs_llm"][f"{h}_vs_{src}"] = {"n": len(x), "percent_agreement": sum(p == q for p, q in x) / len(x),
                                                 "cohens_kappa": A.cohen_kappa([p for p, _ in x], [q for _, q in x])}
if len(humans) >= 2:
    hs = list(humans)
    sh = {a.item_id: a for a in humans[hs[0]]}, {a.item_id: a for a in humans[hs[1]]}
    common = sorted(set(sh[0]) & set(sh[1]))
    if common:
        report["human_vs_human"] = {"n": len(common), "cohens_kappa": A.cohen_kappa([sh[0][i].primary for i in common], [sh[1][i].primary for i in common]),
                                    "percent_agreement": sum(sh[0][i].primary == sh[1][i].primary for i in common) / len(common)}
json.dump(report, open(f"{here}/reports/human_validation_report.json", "w"), indent=1)
print(json.dumps(report, indent=1))
