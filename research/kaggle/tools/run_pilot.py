"""Pilot: agreement of two LLM annotators, human-validation reserve, and preliminary experiments.

E2  train on synthetic (all 20k) -> evaluate on real Spider queries labelled by LLMs (non-reserved items).
    Measures: agreement of synthetic-trained systems with LLM judgements on real queries (transfer), NOT human accuracy.
E3  grouped 5-fold CV *inside* the LLM-consensus labels (non-reserved). Tiny and class-imbalanced; preliminary only.
Usage: run_pilot.py ANNOT_DIR PILOT_ITEMS_JSONL SYNTH_JSONL
"""
import json, os, sys
import numpy as np
from sklearn.model_selection import GroupKFold
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import annotations as A, experiment as E, pilot as P, rules as R

annot, pilot_path, synth_path = sys.argv[1:4]
here = os.path.join(os.path.dirname(__file__), "..")
def load(path, annotator_id):
    out = []
    for l in open(path):
        if l.strip():
            d = json.loads(l)
            out.append(A.Annotation.from_dict({**d, "annotator_id": annotator_id, "annotator_type": "llm"}))
    return out
la = load(f"{annot}/out_claude.jsonl", "claude-sonnet-5-5"); lb = load(f"{annot}/out_codex.jsonl", "gpt-codex")
pairs = P.align(la, lb)
agree = P.agreement_report(pairs)
cons = P.consensus_labels(pairs)
strata = {i: (v["label"] if v["status"] == "agree" else "disagreement") for i, v in cons.items()}
reserve = P.stratified_reserve(strata, 100, seed=20261127)
rset = set(reserve)
ma, mb = {x.item_id: x for x in la}, {x.item_id: x for x in lb}

items0 = {json.loads(l)["item_id"]: json.loads(l) for l in open(pilot_path)}
# provenance-separated label file (no SQL / rows: ids and labels only)
with open(f"{here}/annotations/pilot_llm_labels.jsonl", "w") as f:
    for i in sorted(cons):
        f.write(json.dumps({"item_id": i, "db_id": items0[i]["db_id"], "label_source": cons[i]["label_source"], **{k: v for k, v in cons[i].items() if k != "label_source"},
                            "claude_primary": ma[i].primary, "claude_acceptable": list(ma[i].acceptable), "codex_primary": mb[i].primary,
                            "codex_acceptable": list(mb[i].acceptable), "reserved_for_human_validation": i in rset}) + "\n")
json.dump(sorted(reserve), open(f"{here}/annotations/human_validation_reserve_ids.json", "w"))
json.dump(agree, open(f"{here}/reports/pilot_agreement.json", "w"), indent=1)

items = {json.loads(l)["item_id"]: json.loads(l) for l in open(pilot_path)}
synth = [json.loads(l) for l in open(synth_path)]
Xs, _ = E.featurize(synth)
free = [i for i in sorted(items) if i not in rset]
Xp, Cp = E.featurize([items[i] for i in free])
pos = {i: k for k, i in enumerate(free)}

def eval_set(label_fn):
    sel = [i for i in free if label_fn(i) is not None]
    test = [dict(items[i], label=label_fn(i)[0], acceptable=label_fn(i)[1]) for i in sel]
    return sel, test

def e2(name, fn):
    sel, test = eval_set(fn)
    idx = [pos[i] for i in sel]
    r = E.evaluate_all(synth, test, seed=0, Xtr=Xs, Xte=Xp[idx], cols_te=[Cp[k] for k in idx])
    r["label_set"] = name
    return r

e2s = {"claude_labels": e2("claude_labels", lambda i: (ma[i].primary, set(ma[i].acceptable))),
       "codex_labels": e2("codex_labels", lambda i: (mb[i].primary, set(mb[i].acceptable))),
       "llm_consensus_only": e2("llm_consensus_only", lambda i: (cons[i]["label"], set(cons[i]["acceptable"])) if cons[i]["label"] else None)}

# E3: grouped CV inside consensus labels
sel, test = eval_set(lambda i: (cons[i]["label"], set(cons[i]["acceptable"])) if cons[i]["label"] else None)
idx = [pos[i] for i in sel]; X3 = Xp[idx]; C3 = [Cp[k] for k in idx]; y3 = [t["label"] for t in test]; g3 = [t["db_id"] for t in test]
preds = {s: [None] * len(test) for s in E.SYSTEMS}
for tr, te in GroupKFold(5).split(X3, y3, g3):
    res = E.predict_systems(X3[tr], [y3[k] for k in tr], X3[te], [C3[k] for k in te], 0)
    for s in E.SYSTEMS:
        for k, p in zip(te, res["pred"][s]):
            preds[s][k] = p
el = [R.eligible(X3[k], C3[k]) for k in range(len(test))]
acc = [t["acceptable"] for t in test]
e3 = {"n": len(test), "class_counts": {c: y3.count(c) for c in set(y3)}, "majority_baseline": E.majority_baseline(y3, y3),
      "systems": {s: E.metrics(y3, preds[s], g3, el, acc, 0) for s in E.SYSTEMS}}
report = {"experiment": "pilot_E2_E3", "label_provenance": "LLM annotators (claude-sonnet-5-5, gpt-codex); NOT human",
          "meta": E.run_meta({"pilot_items": len(items), "reserved_for_human_validation": len(reserve), "free_items": len(free),
                              "synthetic_sha256": E.sha256_items(synth), "agreement": {k: agree[k] for k in ("percent_agreement_primary", "cohens_kappa_primary")}}),
          "E2_synthetic_train_to_llm_labelled_real": e2s, "E3_grouped_cv_on_llm_consensus": e3}
json.dump(report, open(f"{here}/reports/pilot_e2_e3.json", "w"), indent=1)
print(json.dumps({"agreement": {k: agree[k] for k in ("n", "percent_agreement_primary", "cohens_kappa_primary", "class_counts_a", "class_counts_b")},
                  "reserve": len(reserve), "free": len(free),
                  "E2": {k: {s: [round(v["systems"][s]["accuracy"], 3), round(v["systems"][s]["macro_f1"], 3), round(v["systems"][s]["semantic_violation_rate"], 3)] for s in E.SYSTEMS} | {"n": v["n_test"], "test_majority": [v["test_majority"]["class"], round(v["test_majority"]["accuracy"], 3)]} for k, v in e2s.items()},
                  "E3": {"n": e3["n"], "majority": e3["majority_baseline"], **{s: [round(e3["systems"][s]["accuracy"], 3), round(e3["systems"][s]["macro_f1"], 3)] for s in E.SYSTEMS}}}, indent=1))
