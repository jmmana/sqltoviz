"""Model-backed recommendation engine (experimental candidate models by default).

Public API (stable): ``Engine(chart_model=None, role_model=None, manifest=None)`` and ``Engine.recommend(sql, columns, rows)``.
Replacing the candidate models with final ones only requires passing different files/manifest (or replacing ``models/manifest.json``);
the API and the result shape do not change. Models are checked against their SHA256 and tensor schema before use.
The result states the model status taken from the manifest ("experimental" for the bundled candidates).
"""
from __future__ import annotations

import json
from pathlib import Path

from . import features as F
from . import rules
from ._contract import BASE_CLASSES, CONTRACT_SHA256, CONTRACT_VERSION, ROLES

MODELS_DIR = Path(__file__).resolve().parent / "models"


class ModelError(ValueError):
    pass


def _np():
    try:
        import numpy as np
    except ImportError as e:  # pragma: no cover
        raise ModelError("numpy and onnxruntime are required for model inference: pip install 'sqltoviz[onnx]'") from e
    return np


class Engine:
    def __init__(self, chart_model=None, role_model=None, manifest=None):
        """chart_model/role_model: path to .onnx, or None (rules-only for that part). manifest: dict with 'chart'/'role' entries
        {file, sha256, status, version}; when given, files are resolved relative to ``MODELS_DIR`` unless absolute and checksums enforced."""
        self.manifest = manifest or {}
        self.chart = self._load("chart", chart_model)
        self.role = self._load("role", role_model)

    @classmethod
    def default(cls) -> "Engine":
        """Engine with the bundled EXPERIMENTAL candidate models (checksum-verified against models/manifest.json)."""
        manifest = json.loads((MODELS_DIR / "manifest.json").read_text())
        return cls(MODELS_DIR / manifest["chart"]["file"], MODELS_DIR / manifest["role"]["file"], manifest)

    def _load(self, kind, path):
        if path is None:
            return None
        from .onnx import load_session
        path = Path(path)
        entry = self.manifest.get(kind)
        if entry is None:
            raise ModelError(f"no manifest entry/checksum for {kind} model: provide manifest={{'{kind}': {{'sha256': ..., 'status': ...}}}}")
        return load_session(path, entry["sha256"], kind=kind)

    @property
    def model_status(self) -> str:
        if self.chart is None:
            return "none (rules only)"
        return self.manifest.get("chart", {}).get("status", "unknown")

    def recommend(self, sql: str, columns: list, rows: list) -> dict:
        """columns: [{'name': str, 'type'?: 'temporal'|'quantitative'|'nominal'|'identifier'}] (or plain names); rows: list of equal-length lists."""
        columns = [{"name": c} if isinstance(c, str) else c for c in columns]
        table, colmat = F.extract(sql, columns, rows)
        rule_class = rules.rule_predict(table, colmat)
        el = rules.eligible(table, colmat)
        warnings = []
        if self.chart is None:
            scores, base, final, changed = None, rule_class, rule_class, False
            warnings.append("No chart model loaded: rules-only recommendation.")
        else:
            np = _np()
            out = self.chart.run(["chart_scores"], {"table_features": np.asarray([table], dtype=np.float32)})[0][0]
            scores = [float(x) for x in out]
            base = BASE_CLASSES[max(range(len(scores)), key=lambda k: (scores[k], -k))]
            final, changed = rules.constrained_choice(scores, table, colmat)
        roles = None
        if self.role is not None:
            np = _np()
            rs = self.role.run(["role_scores"], {"column_features": np.asarray(colmat, dtype=np.float32)})[0]
            roles = [{"column": c["name"], "role": ROLES[max(range(5), key=lambda k: (float(r[k]), -k))], "scores": [float(x) for x in r]}
                     for c, r in zip(columns, rs)]
        status = self.model_status
        if status != "validated":
            warnings.append(f"Model status: {status}. Recommendations are not scientifically validated.")
        return {"contract_version": CONTRACT_VERSION, "contract_sha256": CONTRACT_SHA256, "model_status": status,
                "base_class": base, "final_class": final, "constraint_changed": changed, "rule_class": rule_class,
                "scores": dict(zip(BASE_CLASSES, scores)) if scores else None, "eligible": el, "roles": roles,
                "table_features": table, "column_features": colmat, "warnings": warnings}
