"""Measured label-leakage audit for synthetic data.

Question answered: how well can the label be predicted from the SQL *text alone* (or from table/column
names alone) under grouped cross-validation by schema? Some dependence is structural and legitimate:
the SQL fixes the result *shape* (scalar / category+measure / two categories+measure / time series /
two measures / wide), and shape narrows the label set. With perfect shape knowledge and uniform guessing
inside each shape the best accuracy is the **structural ceiling**. The audit therefore reports
(1) overall accuracy vs that ceiling and (2) accuracy *within* each shape vs chance 1/k - the
latter must be at chance for class-agnostic templates.
"""
from __future__ import annotations

import re
from collections import Counter

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold

from . import features as F
from . import synthgen as G

SHAPE_OF = {"kpi": "scalar", "bar": "cat_quant", "horizontal_bar": "cat_quant", "donut": "cat_quant",
            "stacked_bar": "two_nom_quant", "heatmap": "two_nom_quant", "line": "time_quant", "area": "time_quant",
            "scatter": "quant_quant", "table": "wide"}
_VOCAB = set(w for pool in (G.ENTITIES, G.DIMS, G.MEASURES, G.TIMES) for name in pool for w in name.split("_")) | {"id", "uid", "ref", "order"}


def structural_ceiling(labels) -> float:
    c = Counter(labels)
    by_shape = Counter()
    top = Counter()
    for lab, n in c.items():
        by_shape[SHAPE_OF[lab]] += n
        top[SHAPE_OF[lab]] = max(top[SHAPE_OF[lab]], n)
    return sum(top.values()) / sum(c.values())


def sql_feature_matrix(items) -> np.ndarray:
    return np.array([F.sql_features(i["sql"], []) for i in items], dtype=float)


def token_matrix(items):
    docs = [" ".join(re.findall(r"[a-z_]+", i["sql"].lower())) for i in items]
    return CountVectorizer(binary=True, min_df=5, token_pattern=r"[a-z_]+").fit_transform(docs).toarray()


def name_matrix(items):
    docs = [" ".join(w for w in re.split(r"[^a-z]+", " ".join(i["columns"]).lower() + " " + re.search(r"FROM (\w+)", i["sql"]).group(1))
                     if w in _VOCAB) for i in items]
    return CountVectorizer(binary=True, min_df=5, token_pattern=r"[a-z]+").fit_transform(docs).toarray()


def data_matrix(items) -> np.ndarray:
    return np.array([F.extract(i["sql"], [{"name": c} for c in i["columns"]], i["rows"])[0][16:] for i in items], dtype=float)


def grouped_cv_predict(X, y, groups, seed=0, n_splits=5):
    classes = sorted(set(y))
    proba = np.zeros((len(y), len(classes)))
    for tr, te in GroupKFold(n_splits=n_splits).split(X, y, groups):
        m = RandomForestClassifier(n_estimators=200, min_samples_leaf=2, random_state=seed, n_jobs=1).fit(X[tr], np.array(y)[tr])
        p = m.predict_proba(X[te])
        for j, c in enumerate(m.classes_):
            proba[te, classes.index(c)] = p[:, j]
    return classes, proba


def report(items, seed=0) -> dict:
    y = [i["label"] for i in items]
    groups = [i["db_id"] for i in items]
    out = {"n": len(items), "n_schemas": len(set(groups)), "structural_ceiling_accuracy": structural_ceiling(y),
           "uniform_chance": 1 / len(set(y)), "views": {}}
    for name, X in (("sql_features16", sql_feature_matrix(items)), ("sql_token_bag", token_matrix(items)),
                    ("names_only", name_matrix(items)), ("data_features16_global", data_matrix(items))):
        classes, proba = grouped_cv_predict(X, y, groups, seed)
        pred = [classes[k] for k in proba.argmax(1)]
        within = {}
        for shape in sorted(set(SHAPE_OF.values())):
            idx = [k for k, lab in enumerate(y) if SHAPE_OF[lab] == shape]
            cl = [c for c in classes if SHAPE_OF[c] == shape]
            if len(cl) < 2:
                continue
            ci = [classes.index(c) for c in cl]
            hits = [cl[int(np.argmax(proba[k, ci]))] == y[k] for k in idx]
            within[shape] = {"accuracy": float(np.mean(hits)), "chance": 1 / len(cl), "n": len(idx)}
        out["views"][name] = {"accuracy": float(np.mean([a == b for a, b in zip(pred, y)])),
                              "macro_f1": float(f1_score(y, pred, average="macro")), "within_shape": within}
    return out
