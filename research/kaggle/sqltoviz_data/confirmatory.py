"""Confirmatory-analysis path of PROTOCOL.md (#93, #94), runnable on every label tier with explicit provenance.

Provenance tiers (never merged): ``synthetic``, ``llm`` (LLM annotators, NOT human), ``human`` (the only confirmatory tier) and
``FAKE_DRYRUN`` (a synthetic stand-in used only to exercise the code path; it must never reach a result table).
Every report carries ``provenance`` and ``confirmatory``; ``write_report`` refuses to put FAKE_DRYRUN output anywhere except a
file whose name contains FAKE, and refuses to mark non-human tiers as confirmatory.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score

from . import experiment as E
from . import rules as R

SYNTHETIC, LLM, HUMAN, FAKE = "synthetic", "llm", "human", "FAKE_DRYRUN"
LLM_REF = "llm_reference"   # declared design (2026-11-28): reference = agreement of LLM annotators; never human, never confirmatory
TIERS = (SYNTHETIC, LLM, LLM_REF, HUMAN, FAKE)
MIN_CLASS_SUPPORT = 5          # PROTOCOL.md section 3: classes with fewer human-labelled items are reported but excluded from macro-F1
BOOTSTRAP_REPS = 2000          # PROTOCOL.md section 5
BANNER = {SYNTHETIC: "exploratory: agreement with the synthetic generator's convention, not human preference",
          LLM: "exploratory: agreement with LLM annotators, not human validation",
          LLM_REF: "exploratory: reference is the majority of LLM annotators (3 models + 1 AI workbook of unknown model, not independent); there is no human validation",
          HUMAN: "confirmatory per PROTOCOL.md",
          FAKE: "FAKE DRY-RUN: random stand-in labels; numbers are meaningless and must not appear in any result table"}


def resolve_truth(rows: list, min_annotators: int = 2) -> dict:
    """rows: dicts item_id, primary, acceptable (one per annotator). Majority vote; ties are NOT guessed.
    Returns {'truth': {item: {label, acceptable, n_annotators}}, 'unresolved': [item ids needing adjudication], 'single_annotator': [...]}."""
    by: dict = {}
    for r in rows:
        by.setdefault(r["item_id"], []).append(r)
    truth, unresolved, single = {}, [], []
    for i, rs in sorted(by.items()):
        if len(rs) < min_annotators:
            single.append(i)
            continue
        c = Counter(r["primary"] for r in rs).most_common()
        if len(c) > 1 and c[0][1] == c[1][1]:
            unresolved.append(i)
            continue
        truth[i] = {"label": c[0][0], "acceptable": sorted({a for r in rs for a in r["acceptable"]} | {c[0][0]}), "n_annotators": len(rs)}
    return {"truth": truth, "unresolved": unresolved, "single_annotator": single}


def supported_classes(labels: list, min_support: int = MIN_CLASS_SUPPORT) -> tuple:
    cnt = Counter(labels)
    kept = [c for c in R.CLASSES if cnt[c] >= min_support]
    excluded = {c: cnt[c] for c in R.CLASSES if 0 < cnt[c] < min_support}
    return kept, excluded


def paired_cluster_bootstrap(y, preds: dict, groups, labels, reps: int = BOOTSTRAP_REPS, seed: int = 0) -> dict:
    """Same cluster resamples for every system. Returns per-system macro-F1 CI and ALL pairwise differences (no selective reporting).
    A difference is 'excludes_zero' only when its 95 % percentile CI does not contain 0 (the claim rule of PROTOCOL.md)."""
    y, groups = np.array(y), np.array(groups)
    ug = np.unique(groups)
    idx_by = {g: np.where(groups == g)[0] for g in ug}
    names = list(preds)
    P = {n: np.array(preds[n]) for n in names}
    rng = np.random.default_rng(seed)
    vals = {n: [] for n in names}
    for _ in range(reps):
        idx = np.concatenate([idx_by[g] for g in rng.choice(ug, len(ug), replace=True)])
        for n in names:
            vals[n].append(f1_score(y[idx], P[n][idx], labels=labels, average="macro", zero_division=0))
    ci = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
    out = {"reps": reps, "seed": seed, "n_clusters": int(len(ug)), "macro_f1_ci95": {n: ci(vals[n]) for n in names}, "pairwise": {}}
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            d = np.array(vals[names[a]]) - np.array(vals[names[b]])
            lo, hi = ci(d)
            out["pairwise"][f"{names[a]} - {names[b]}"] = {"mean_diff": float(d.mean()), "ci95": [lo, hi], "excludes_zero": bool(lo > 0 or hi < 0)}
    return out


def analyze(train_items: list, test_items: list, truth: dict, provenance: str, seed: int = 0, reps: int = BOOTSTRAP_REPS) -> dict:
    """Train the five systems on ``train_items`` (labelled; synthetic and never reserved) and evaluate on ``test_items`` against ``truth``
    (item_id -> {label, acceptable}). Items without truth are dropped and counted. Rows rejected by the contract would raise, not vanish."""
    if provenance not in TIERS:
        raise ValueError(f"unknown provenance {provenance!r}")
    ids = [i for i in sorted(it["item_id"] for it in test_items) if i in truth]
    byid = {it["item_id"]: it for it in test_items}
    test = [dict(byid[i], label=truth[i]["label"], acceptable=truth[i].get("acceptable") or [truth[i]["label"]]) for i in ids]
    if not test:
        raise ValueError("no test items with a label")
    if {i["item_id"] for i in train_items} & set(ids):
        raise ValueError("train and test overlap")
    Xtr, _ = E.featurize(train_items)
    Xte, cols = E.featurize(test)
    ytr, yte = [i["label"] for i in train_items], [i["label"] for i in test]
    res = E.predict_systems(Xtr, ytr, Xte, cols, seed)
    el = [R.eligible(Xte[k], cols[k]) for k in range(len(test))]
    groups, acc = [i.get("db_id", i["item_id"]) for i in test], [set(i["acceptable"]) for i in test]
    labels, excluded = supported_classes(yte)
    systems = {s: E.metrics(yte, res["pred"][s], groups, el, acc, seed) for s in E.SYSTEMS}
    for s in E.SYSTEMS:    # macro-F1 restricted to classes with enough support (protocol rule)
        systems[s]["macro_f1_supported"] = float(f1_score(yte, res["pred"][s], labels=labels, average="macro", zero_division=0)) if labels else None
    maj = E.majority_baseline(["table"] * len(yte), yte)
    boot = paired_cluster_bootstrap(yte, {**res["pred"], "always_table": ["table"] * len(yte)}, groups, labels, reps, seed) if labels else None
    return {"provenance": provenance, "confirmatory": provenance == HUMAN, "banner": BANNER[provenance],
            "n_test": len(test), "n_without_truth": len(test_items) - len(test), "n_train": len(train_items),
            "class_support": dict(Counter(yte)), "macro_f1_classes": labels, "classes_excluded_low_support": excluded,
            "always_table_baseline": maj, "systems": systems, "paired_cluster_bootstrap": boot, "meta": E.run_meta({})}


def write_report(report: dict, path) -> Path:
    """Guarded writer. FAKE output only to a path containing 'FAKE'; non-human tiers can never claim confirmatory status."""
    p = Path(path)
    if report.get("provenance") not in TIERS:
        raise ValueError("report has no valid provenance")
    if report["provenance"] == FAKE and "FAKE" not in p.name:
        raise ValueError("FAKE_DRYRUN output must go to a file whose name contains FAKE")
    if report["provenance"] != FAKE and "FAKE" in p.name:
        raise ValueError("only FAKE_DRYRUN reports may use a FAKE file name")
    if report.get("confirmatory") and report["provenance"] != HUMAN:
        raise ValueError("only human provenance can be confirmatory")
    if report["provenance"] == FAKE and "reports" in p.resolve().parts and "dryrun" not in p.resolve().parts:
        raise ValueError("FAKE_DRYRUN output must not be written into reports/ (use a dryrun directory or a temp directory)")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(report, indent=1))
    return p


def fake_dry_run(workdir, n_cases: int = 40, seed: int = 7, reps: int = 200) -> dict:
    """Exercise workbook -> fake fill -> ingest -> truth -> analysis on SYNTHETIC stand-in cases with RANDOM answers.
    Everything it writes is under ``workdir`` and named FAKE; the returned report has provenance FAKE_DRYRUN."""
    import random
    from openpyxl import load_workbook
    from . import human_validation as H
    from . import synthgen as G
    from .annotations import BASE_CLASSES
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    pool = G.generate(max(n_cases // 5, 8), seed=seed, n_schemas=30)
    cases = [dict(it, item_id=f"FAKE_{it['item_id']}") for it in random.Random(seed).sample(pool, n_cases)]
    train = [dict(it, item_id=f"FAKE_TRAIN_{it['item_id']}") for it in G.generate(30, seed=seed + 1, n_schemas=40)]
    wb_path, key_path = workdir / "FAKE_workbook.xlsx", workdir / "FAKE_key.csv"
    H.build_workbook([{k: c[k] for k in ("item_id", "sql", "columns", "rows", "db_id")} for c in cases], wb_path, key_path, seed=seed)
    rows, first = [], {}
    for ann in ("FAKE-A", "FAKE-B"):
        rng = random.Random(f"{seed}-{ann}")
        wb = load_workbook(wb_path)
        ws = wb["Cases"]
        for r in range(2, ws.max_row + 1):
            pick = rng.choice(BASE_CLASSES[:4] + ("table",) * 3)
            if ann == "FAKE-B" and rng.random() < 0.7:      # B mostly copies A so that some items reach a majority
                pick = first[ws.cell(r, 1).value]
            first[ws.cell(r, 1).value] = pick if ann == "FAKE-A" else first[ws.cell(r, 1).value]
            ws.cell(r, 5, pick)
            ws.cell(r, 16, rng.choice((1, 2, 3)))
        filled = workdir / f"FAKE_filled_{ann}.xlsx"
        wb.save(filled)
        anns, problems = H.ingest(filled, key_path, ann)
        assert not problems, problems
        rows += [{"item_id": a.item_id, "primary": a.primary, "acceptable": list(a.acceptable)} for a in anns]
    res = resolve_truth(rows)
    rep = analyze(train, cases, res["truth"], FAKE, seed=0, reps=reps)
    rep.update({"unresolved_items": res["unresolved"], "single_annotator_items": res["single_annotator"],
                "warning": "FAKE: items, labels and annotators are synthetic stand-ins created for a code-path test"})
    return rep
