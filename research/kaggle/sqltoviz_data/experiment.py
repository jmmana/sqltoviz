"""Experiment runner: five systems, one protocol, full provenance.

Systems (all consume only frozen-contract features):
  rules            deterministic rules-only engine (rules.py)
  sql_only         random forest on the 16 SQL features
  data_only        random forest on the 16 global data features
  hybrid           random forest on all 32 table features
  hybrid_semantic  hybrid + hard semantic constraints (highest-scoring *eligible* class, else table)
Hyper-parameters are fixed defaults (no tuning), so validation data is not consumed here.
Every result file records contract version/SHA256, seeds, dataset hashes, library versions, git commit.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from collections import Counter
from pathlib import Path

import numpy as np
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support

from . import features as F
from . import rules as R

CLASSES = R.CLASSES
SYSTEMS = ("rules", "sql_only", "data_only", "hybrid", "hybrid_semantic")
VIEWS = {"sql_only": slice(0, 16), "data_only": slice(16, 32), "hybrid": slice(0, 32)}


def featurize(items: list) -> tuple:
    """Return (table matrix [n,32] float32, list of column matrices). Items need sql, columns, rows."""
    tabs, cols = [], []
    for it in items:
        t, c = F.extract(it["sql"], [{"name": n} for n in it["columns"]], it["rows"])
        tabs.append(t)
        cols.append(c)
    return np.stack(tabs), cols


def make_rf(seed: int) -> RandomForestClassifier:
    return RandomForestClassifier(n_estimators=300, min_samples_leaf=2, class_weight="balanced", random_state=seed, n_jobs=-1)


def _proba_full(model, X) -> np.ndarray:
    p = model.predict_proba(X)
    out = np.zeros((len(X), len(CLASSES)), dtype=np.float32)
    for j, c in enumerate(model.classes_):
        out[:, CLASSES.index(c)] = p[:, j]
    return out


def predict_systems(Xtr, ytr, Xte, cols_te, seed: int) -> dict:
    preds, scores = {}, {}
    preds["rules"] = [R.rule_predict(Xte[i], cols_te[i]) for i in range(len(Xte))]
    scores["rules"] = np.stack([R.rule_scores(Xte[i], cols_te[i]) for i in range(len(Xte))])
    for name, sl in VIEWS.items():
        m = make_rf(seed).fit(Xtr[:, sl], ytr)
        scores[name] = _proba_full(m, Xte[:, sl])
        preds[name] = [CLASSES[k] for k in scores[name].argmax(1)]
    sem, changed = [], []
    for i in range(len(Xte)):
        p, ch = R.constrained_choice(scores["hybrid"][i], Xte[i], cols_te[i])
        sem.append(p)
        changed.append(ch)
    preds["hybrid_semantic"] = sem
    scores["hybrid_semantic_changed"] = np.array(changed)
    return {"pred": preds, "scores": scores}


def cluster_bootstrap_f1(y, pred, groups, labels, reps=500, seed=0):
    rng = np.random.default_rng(seed)
    y, pred, groups = np.array(y), np.array(pred), np.array(groups)
    ug = np.unique(groups)
    idx_by = {g: np.where(groups == g)[0] for g in ug}
    vals = []
    for _ in range(reps):
        pick = rng.choice(ug, len(ug), replace=True)
        idx = np.concatenate([idx_by[g] for g in pick])
        vals.append(f1_score(y[idx], pred[idx], labels=labels, average="macro", zero_division=0))
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def metrics(y, pred, groups, eligible_flags, acceptable=None, seed=0) -> dict:
    labels = [c for c in CLASSES if c in set(y)]
    p, r, f, s = precision_recall_fscore_support(y, pred, labels=list(CLASSES), zero_division=0)
    per = {c: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]), "support": int(s[i])} for i, c in enumerate(CLASSES)}
    out = {"n": len(y), "accuracy": float(np.mean(np.array(y) == np.array(pred))),
           "macro_f1": float(f1_score(y, pred, labels=labels, average="macro", zero_division=0)),
           "macro_f1_classes": labels, "macro_f1_ci95_cluster_bootstrap": cluster_bootstrap_f1(y, pred, groups, labels, seed=seed),
           "per_class": per,
           "semantic_violation_rate": float(np.mean([not e[pr] for e, pr in zip(eligible_flags, pred)])),
           "table_fallback_rate": float(np.mean(np.array(pred) == "table")),
           "confusion_matrix": {"labels": list(CLASSES), "matrix": confusion_matrix(y, pred, labels=list(CLASSES)).tolist()}}
    if acceptable is not None:
        out["acceptable_hit_rate"] = float(np.mean([pr in a for pr, a in zip(pred, acceptable)]))
    return out


def majority_baseline(ytr, yte) -> dict:
    m = Counter(ytr).most_common(1)[0][0]
    return {"class": m, "accuracy": float(np.mean(np.array(yte) == m))}


def evaluate_all(train, test, seed=0, Xtr=None, Xte=None, cols_te=None) -> dict:
    if Xtr is None:
        Xtr, _ = featurize(train)
    if Xte is None or cols_te is None:
        Xte, cols_te = featurize(test)
    ytr, yte = [i["label"] for i in train], [i["label"] for i in test]
    res = predict_systems(Xtr, ytr, Xte, cols_te, seed)
    el = [R.eligible(Xte[i], cols_te[i]) for i in range(len(Xte))]
    groups = [i["db_id"] for i in test]
    acc = [set(i.get("acceptable") or [i["label"]]) for i in test]
    tmc = Counter(yte).most_common(1)[0]
    out = {"n_train": len(train), "n_test": len(test), "majority_baseline": majority_baseline(ytr, yte),
           "test_majority": {"class": tmc[0], "accuracy": tmc[1] / len(yte)},
           "train_class_counts": dict(Counter(ytr)), "test_class_counts": dict(Counter(yte)), "systems": {}}
    for s in SYSTEMS:
        out["systems"][s] = metrics(yte, res["pred"][s], groups, el, acc, seed)
    out["systems"]["hybrid_semantic"]["constraint_changed_rate"] = float(res["scores"]["hybrid_semantic_changed"].mean())
    return out


def sha256_items(items) -> str:
    h = hashlib.sha256()
    for it in sorted(items, key=lambda x: x["item_id"]):
        h.update(json.dumps({k: it[k] for k in ("item_id", "sql", "label")}, sort_keys=True).encode())
    return h.hexdigest()


def run_meta(extra: dict | None = None) -> dict:
    def sh(*a):
        try:
            return subprocess.run(a, capture_output=True, text=True, cwd=Path(__file__).parent).stdout.strip()
        except OSError:
            return ""
    F.load_contract()   # verifies pinned SHA256
    meta = {"contract_version": F.CONTRACT_VERSION, "contract_sha256": F.CONTRACT_SHA256,
            "git_commit": sh("git", "rev-parse", "HEAD"), "python": platform.python_version(), "sklearn": sklearn.__version__,
            "numpy": np.__version__, "model": "RandomForest(n=300,min_leaf=2,balanced)", "tuning": "none (fixed defaults)",
            "rules_thresholds": {"DONUT_MAX_K": R.DONUT_MAX_K, "HEATMAP_MIN_K": R.HEATMAP_MIN_K, "LONG_LABEL": R.LONG_LABEL,
                                 "BAR_MAX_ROWS": R.BAR_MAX_ROWS, "SCATTER_MIN_ROWS": R.SCATTER_MIN_ROWS}}
    meta.update(extra or {})
    return meta


ABLATION_GROUPS = {
    "sql_clauses": ["join_count", "subquery_cte_count", "has_group_by", "group_expression_count", "has_order_by", "has_limit",
                    "normalized_limit", "has_having", "has_distinct"],
    "sql_semantic": ["ascending_temporal_order", "has_temporal_function", "has_window", "aggregate_count", "calculated_projection_ratio"],
    "sql_size": ["log_token_count", "parenthesis_depth"],
    "data_size": ["log_row_count", "single_row", "small_rows", "large_rows"],
    "data_types": ["column_count", "temporal_count", "quantitative_count", "nominal_count", "identifier_count", "quantitative_ratio", "nominal_ratio"],
    "data_cardinality": ["non_null_density", "max_nominal_relative_cardinality", "min_nominal_cardinality", "crossed_structure", "mean_nominal_entropy"],
}


def ablate(Xtr, ytr, Xte, yte, seed: int = 0) -> dict:
    """Leave-one-group-out ablation of the 32 table features (hybrid random forest). Reports macro-F1 and delta vs full."""
    assert sorted(n for g in ABLATION_GROUPS.values() for n in g) == sorted(R.T), "ablation groups must partition the 32 features"
    labels = [c for c in CLASSES if c in set(yte)]

    def f1(cols):
        m = make_rf(seed).fit(Xtr[:, cols], ytr)
        pred = [CLASSES[k] for k in _proba_full(m, Xte[:, cols]).argmax(1)]
        return float(f1_score(yte, pred, labels=labels, average="macro", zero_division=0))

    allc = list(range(32))
    full = f1(allc)
    out = {"full": full, "groups": {}}
    for g, names in ABLATION_GROUPS.items():
        drop = {R.T[n] for n in names}
        v = f1([c for c in allc if c not in drop])
        out["groups"][g] = {"macro_f1_without": v, "delta_vs_full": v - full, "n_features": len(names)}
    return out
