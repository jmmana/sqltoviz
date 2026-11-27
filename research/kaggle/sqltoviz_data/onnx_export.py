"""ONNX export + verification of the chart model (contract: table_features[batch,32] -> chart_scores[batch,10]).

The classifier is trained on integer class indices in contract order, so probabilities come out in
``base_classes`` order (sklearn would otherwise sort class names alphabetically). Output ``chart_scores`` are
probabilities, not final-chart confidence (contract score_semantics).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
from sklearn.ensemble import RandomForestClassifier

from . import features as F

CLASSES = tuple(F.contract()["model_io"]["base_classes"])


def fit_contract_model(X: np.ndarray, y_names: list, seed: int = 0, n_estimators: int = 100, min_samples_leaf: int = 5):
    if X.shape[1] != 32:
        raise ValueError("table_features must have 32 columns")
    missing = set(CLASSES) - set(y_names)
    if missing:
        raise ValueError(f"all 10 base classes must be present in training; missing {sorted(missing)}")
    y = np.array([CLASSES.index(c) for c in y_names])
    m = RandomForestClassifier(n_estimators=n_estimators, min_samples_leaf=min_samples_leaf, class_weight="balanced",
                               random_state=seed, n_jobs=-1)
    return m.fit(X.astype(np.float32), y)


def export_chart_model(model, path) -> Path:
    assert list(model.classes_) == list(range(len(CLASSES))), "model must be trained on contract-ordered class indices"
    onx = convert_sklearn(model, initial_types=[("table_features", FloatTensorType([None, 32]))],
                          options={id(model): {"zipmap": False}}, target_opset={"": 17, "ai.onnx.ml": 3})
    g = onx.graph
    for node in g.node:                                   # rename probabilities -> chart_scores
        for k, o in enumerate(node.output):
            if o == "probabilities":
                node.output[k] = "chart_scores"
        for k, i in enumerate(node.input):
            if i == "probabilities":
                node.input[k] = "chart_scores"
    keep = [o for o in g.output if o.name != "label"]
    for o in keep:
        if o.name == "probabilities":
            o.name = "chart_scores"
    del g.output[:]
    g.output.extend(keep)
    g.output[0].type.tensor_type.shape.dim[1].dim_value = len(CLASSES)
    onx.metadata_props.add(key="contract_version", value=F.CONTRACT_VERSION)
    onx.metadata_props.add(key="contract_sha256", value=F.CONTRACT_SHA256)
    onx.metadata_props.add(key="class_order", value=json.dumps(list(CLASSES)))
    onx.metadata_props.add(key="score_semantics", value="probabilities in class order; not final-chart confidence")
    onnx.checker.check_model(onx)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(onx.SerializeToString())
    return path


def session(path) -> ort.InferenceSession:
    return ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])


def predict_onnx(sess, X: np.ndarray) -> np.ndarray:
    return sess.run(["chart_scores"], {"table_features": np.asarray(X, dtype=np.float32)})[0]


def verify_against_sklearn(model, sess, X: np.ndarray, atol: float = 1e-6, rtol: float = 1e-6) -> dict:
    ref = model.predict_proba(X.astype(np.float32))
    got = predict_onnx(sess, X)
    diff = np.abs(ref - got)
    return {"n": int(len(X)), "max_abs_diff": float(diff.max()), "within_tolerance": bool(np.allclose(ref, got, atol=atol, rtol=rtol)),
            "argmax_equal_rate": float((ref.argmax(1) == got.argmax(1)).mean()),
            "row_sums_max_dev": float(np.abs(got.sum(1) - 1).max()), "atol": atol, "rtol": rtol}


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
