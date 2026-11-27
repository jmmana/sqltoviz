"""Stage license-separated Kaggle dataset folders from notebook outputs, with checksum verification.

Safety defaults (all must be overridden explicitly):
* verifies every file against MANIFEST.json (sha256) and the pinned contract SHA256;
* refuses smoke-mode outputs (``allow_smoke``) and CANDIDATE models (``allow_candidate``);
* never uploads unless ``upload`` is called; uploads are created *private* (Kaggle default, never ``--public``).
Two datasets are produced so licenses never mix: Apache-2.0 (own code/data/model/parity) and CC BY-SA 4.0
(material derived from Spider/BIRD plus pilot labels).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import features as F
from .pipeline import sha256_file

NAMESPACES = {
    "apache-2.0": {"slug": "sqltoviz-synthetic-model-parity", "title": "SqlToViz synthetic data, model and parity",
                   "license": "Apache 2.0", "dirs": ("apache-2.0", "model", "parity", "reports")},
    "cc-by-sa-4.0": {"slug": "sqltoviz-real-derived-ccbysa", "title": "SqlToViz Spider/BIRD-derived features CC BY-SA",
                     "license": "CC BY-SA 4.0", "dirs": ("cc-by-sa-4.0", "llm-labels")},
}
ATTRIBUTION = ("Derived from Spider (Yu et al., Yale LILY) and BIRD (Li et al.), both CC BY-SA 4.0. Changes: SQL executed, results converted to "
               "SqlVizSpec-v1.0.0 features, deduplicated, split by database; LLM-generated chart labels (not human). ShareAlike applies.\n")


class PublishError(RuntimeError):
    pass


def verify_manifest(out: Path) -> dict:
    man = json.loads((out / "MANIFEST.json").read_text())
    if man["contract_sha256"] != F.CONTRACT_SHA256:
        raise PublishError("manifest was built with a different contract")
    for rel, e in man["files"].items():
        p = out / rel
        if not p.exists() or sha256_file(p) != e["sha256"]:
            raise PublishError(f"checksum mismatch or missing file: {rel}")
    return man


def stage(out, staging, username: str = "USERNAME", allow_smoke: bool = False, allow_candidate: bool = False) -> dict:
    out, staging = Path(out), Path(staging)
    man = verify_manifest(out)
    if man.get("mode") != "full" and not allow_smoke:
        raise PublishError("outputs come from smoke mode; refusing (allow_smoke=True to override)")
    card = out / "model" / "MODEL_CARD.json"
    if card.exists() and "CANDIDATE" in json.loads(card.read_text()).get("status", "") and not allow_candidate:
        raise PublishError("model is a CANDIDATE; refusing to publish (allow_candidate=True to override)")
    result = {}
    for ns, cfg in NAMESPACES.items():
        d = staging / ns
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        files = {}
        for rel, e in man["files"].items():
            if e["namespace"] == ns and rel.split("/")[0] in cfg["dirs"]:
                (d / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(out / rel, d / rel)
                files[rel] = e["sha256"]
        if not files:
            continue
        (d / "CHECKSUMS.sha256").write_text("".join(f"{h}  {r}\n" for r, h in sorted(files.items())))
        (d / "PROVENANCE.json").write_text(json.dumps({"contract_version": man["contract_version"], "contract_sha256": man["contract_sha256"],
                                                       "repo_commit": man.get("repo_commit"), "mode": man.get("mode"),
                                                       "label_provenance": {"synthetic": "by construction", "llm": "pilot", "human": "none"}}, indent=1))
        if ns == "cc-by-sa-4.0":
            (d / "ATTRIBUTION.md").write_text(ATTRIBUTION)
        (d / "dataset-metadata.json").write_text(json.dumps({"title": cfg["title"], "id": f"{username}/{cfg['slug']}",
                                                             "licenses": [{"name": cfg["license"]}]}, indent=1))
        result[ns] = {"dir": str(d), "n_files": len(files)}
    return result


def upload(staged: dict) -> list:
    """Create private Kaggle datasets from staged folders (explicit call only)."""
    out = []
    for ns, info in staged.items():
        r = subprocess.run(["kaggle", "datasets", "create", "-p", info["dir"], "--dir-mode", "zip"], capture_output=True, text=True)
        out.append({"namespace": ns, "returncode": r.returncode, "stdout": r.stdout[-300:], "stderr": r.stderr[-300:]})
    return out
