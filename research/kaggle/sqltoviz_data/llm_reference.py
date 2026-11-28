"""LLM-reference evaluation on the reserved 100 items (declared design, 2026-11-28: NO human validation).

Reference truth = plurality label over four LLM annotators (pilot Claude, pilot Codex, Claude single pass, AI-generated workbook of
unknown model). They are NOT independent (two are the same model family; one model is unknown) and none is human. Ties are listed and
excluded from scoring, never guessed. Every output carries provenance ``llm_reference`` and ``confirmatory: false``."""
from __future__ import annotations

import csv
import json
from collections import Counter
from itertools import combinations
from pathlib import Path

from sklearn.metrics import cohen_kappa_score

from . import confirmatory as C

ANNOTATORS = ("pilot_claude", "pilot_codex", "claude_single_pass", "ai_workbook_unknown_model")


def load_annotators(kaggle: Path) -> dict:
    """annotator -> {item_id: {primary, acceptable}} for the 100 reserved items (case ids mapped through the key)."""
    kaggle = Path(kaggle)
    key = {r["case_id"]: r["item_id"] for r in csv.DictReader(open(kaggle / "human_validation" / "human_validation_key.csv"))}
    out = {a: {} for a in ANNOTATORS}
    for l in open(kaggle / "annotations" / "pilot_llm_labels.jsonl"):
        d = json.loads(l)
        if d["reserved_for_human_validation"]:
            out["pilot_claude"][d["item_id"]] = {"primary": d["claude_primary"], "acceptable": d["claude_acceptable"]}
            out["pilot_codex"][d["item_id"]] = {"primary": d["codex_primary"], "acceptable": d["codex_acceptable"]}
    for name, f in (("claude_single_pass", "claude_labels_reserved100.jsonl"), ("ai_workbook_unknown_model", "ai_workbook_labels_reserved100.jsonl")):
        for l in open(kaggle / "annotations" / f):
            d = json.loads(l)
            assert d["human"] is False
            out[name][key[d["case_id"]]] = {"primary": d["label"], "acceptable": d["acceptable"]}
    if any(len(v) != 100 for v in out.values()):
        raise ValueError({k: len(v) for k, v in out.items()})
    return out


def agreement(ann: dict) -> dict:
    ids = sorted(ann[ANNOTATORS[0]])
    pair = {}
    for a, b in combinations(ANNOTATORS, 2):
        ya, yb = [ann[a][i]["primary"] for i in ids], [ann[b][i]["primary"] for i in ids]
        pair[f"{a} vs {b}"] = {"percent_agreement": sum(x == y for x, y in zip(ya, yb)) / len(ids), "cohen_kappa": float(cohen_kappa_score(ya, yb))}
    unanimous = sum(len({ann[a][i]["primary"] for a in ANNOTATORS}) == 1 for i in ids)
    return {"pairwise": pair, "unanimous_items": unanimous, "n": len(ids)}


def reference(ann: dict) -> dict:
    rows = [dict(item_id=i, **v) for a in ANNOTATORS for i, v in ann[a].items()]
    res = C.resolve_truth(rows, min_annotators=len(ANNOTATORS))
    by = {}
    for r in rows:
        by.setdefault(r["item_id"], []).append(r["primary"])
    res["votes_strength"] = dict(Counter(max(Counter(by[i]).values()) for i in res["truth"]))   # 4 = unanimous, 3, 2 (plurality of 2 vs 1+1)
    res["tie_votes"] = {i: sorted(by[i]) for i in res["unresolved"]}
    return res


def evaluate(items: list, ann: dict, train: list, reps: int = C.BOOTSTRAP_REPS, seed: int = 0) -> dict:
    ref = reference(ann)
    main = C.analyze(train, items, ref["truth"], C.LLM_REF, seed=seed, reps=reps)
    per = {}
    for a in ANNOTATORS:
        t = {i: {"label": v["primary"], "acceptable": sorted(set(v["acceptable"]) | {v["primary"]})} for i, v in ann[a].items()}
        r = C.analyze(train, items, t, C.LLM_REF, seed=seed, reps=reps)
        per[a] = {k: r[k] for k in ("n_test", "class_support", "macro_f1_classes", "classes_excluded_low_support", "always_table_baseline", "systems", "paired_cluster_bootstrap")}
    majority_share = max(main["class_support"].values()) / main["n_test"]
    main.update({"annotators": list(ANNOTATORS), "annotator_independence": "NOT independent: pilot_claude and claude_single_pass are the same model family; ai_workbook_unknown_model is an AI of unknown identity; none is human",
                 "truth_rule": "plurality over four annotators; unique-top required; ties listed and excluded", "ties_excluded": ref["unresolved"], "tie_votes": ref["tie_votes"],
                 "vote_strength_counts": ref["votes_strength"], "agreement": agreement(ann), "per_annotator_scores": per,
                 "class_balance_caveat": f"largest class share in the reference = {majority_share:.2f}; accuracy is dominated by it and macro-F1 over a handful of rare-class items is unstable",
                 "human_validation": "none (owner decision 2026-11-28)"})
    return main
