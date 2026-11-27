import json

import pytest

from sqltoviz_data import pipeline as P
from sqltoviz_data import publish as PB


def mkout(tmp_path, mode="full", status="FINAL"):
    out = tmp_path / "out"
    for rel, ns, txt in [("apache-2.0/a.jsonl", "apache-2.0", "a"), ("cc-by-sa-4.0/r.jsonl", "cc-by-sa-4.0", "r"),
                         ("llm-labels/l.jsonl", "cc-by-sa-4.0", "l"), ("model/m.onnx", "apache-2.0", "m"), ("parity/g.json", "apache-2.0", "g")]:
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(txt)
    (out / "model/MODEL_CARD.json").write_text(json.dumps({"status": status}))
    files = {"apache-2.0/a.jsonl": "apache-2.0", "cc-by-sa-4.0/r.jsonl": "cc-by-sa-4.0", "llm-labels/l.jsonl": "cc-by-sa-4.0",
             "model/m.onnx": "apache-2.0", "model/MODEL_CARD.json": "apache-2.0", "parity/g.json": "apache-2.0"}
    P.write_manifest(out, files, {"mode": mode, "repo_commit": "abc"})
    return out


def test_stage_separates_licenses_and_writes_checksums(tmp_path):
    out = mkout(tmp_path)
    r = PB.stage(out, tmp_path / "st", "user")
    ap, cc = tmp_path / "st/apache-2.0", tmp_path / "st/cc-by-sa-4.0"
    assert {p.name for p in (ap / "model").iterdir()} == {"m.onnx", "MODEL_CARD.json"} and (ap / "parity/g.json").exists()
    assert (cc / "cc-by-sa-4.0/r.jsonl").exists() and (cc / "llm-labels/l.jsonl").exists() and (cc / "ATTRIBUTION.md").exists()
    assert not (ap / "cc-by-sa-4.0").exists() and not (cc / "model").exists()          # no license mixing
    assert json.loads((ap / "dataset-metadata.json").read_text())["licenses"] == [{"name": "Apache 2.0"}]
    assert json.loads((cc / "dataset-metadata.json").read_text())["licenses"] == [{"name": "CC BY-SA 4.0"}]
    assert "m.onnx" in (ap / "CHECKSUMS.sha256").read_text() and r["apache-2.0"]["n_files"] == 4


def test_refuses_smoke_candidate_and_tampering(tmp_path):
    with pytest.raises(PB.PublishError, match="smoke"):
        PB.stage(mkout(tmp_path / "a", mode="smoke"), tmp_path / "s1")
    with pytest.raises(PB.PublishError, match="CANDIDATE"):
        PB.stage(mkout(tmp_path / "b", status="CANDIDATE - not final"), tmp_path / "s2")
    PB.stage(mkout(tmp_path / "c", status="CANDIDATE - not final"), tmp_path / "s3", allow_candidate=True)
    out = mkout(tmp_path / "d")
    (out / "parity/g.json").write_text("tampered")
    with pytest.raises(PB.PublishError, match="checksum"):
        PB.stage(out, tmp_path / "s4")
