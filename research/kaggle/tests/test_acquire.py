import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from sqltoviz_data import acquire as A


def make_zip(path: Path, entries: dict[str, bytes]) -> str:
    with zipfile.ZipFile(path, "w") as z:
        for k, v in entries.items():
            z.writestr(k, v)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spec_for(src: Path, sha, tmp_name="x.zip"):
    return {"namespace": "ns", "license": "L", "url": src.as_uri(), "filename": tmp_name,
            "size": src.stat().st_size, "sha256": sha, "extract_root": "out"}


def test_happy_path_and_skips_macosx(tmp_path):
    src = tmp_path / "src.zip"
    sha = make_zip(src, {"a/b.txt": b"hi", "__MACOSX/a/._b.txt": b"junk"})
    r = A.acquire("t", spec_for(src, sha), tmp_path / "data")
    assert r["n_files"] == 1 and r["sha256"] == sha and r["pinned"]
    assert (tmp_path / "data/ns/out/a/b.txt").read_bytes() == b"hi"
    assert not (tmp_path / "data/ns/out/__MACOSX").exists()


def test_checksum_mismatch_rejected_and_deleted(tmp_path):
    src = tmp_path / "src.zip"
    make_zip(src, {"a": b"1"})
    with pytest.raises(A.AcquisitionError, match="sha256"):
        A.acquire("t", spec_for(src, "0" * 64), tmp_path / "data")
    assert not (tmp_path / "data/ns/_downloads/x.zip").exists()


def test_size_mismatch_rejected(tmp_path):
    src = tmp_path / "src.zip"
    sha = make_zip(src, {"a": b"1"})
    s = spec_for(src, sha)
    s["size"] += 1
    with pytest.raises(A.AcquisitionError, match="size"):
        A.acquire("t", s, tmp_path / "data")


def test_unpinned_refused_unless_tofu(tmp_path):
    src = tmp_path / "src.zip"
    make_zip(src, {"a": b"1"})
    with pytest.raises(A.AcquisitionError, match="not pinned"):
        A.acquire("t", spec_for(src, None), tmp_path / "data")
    r = A.acquire("t", spec_for(src, None), tmp_path / "data", trust_on_first_use=True)
    assert r["pinned"] is False and len(r["sha256"]) == 64


@pytest.mark.parametrize("bad", ["../evil.txt", "/abs.txt", "a/../../evil.txt", "C:/x.txt"])
def test_zip_slip_rejected(tmp_path, bad):
    src = tmp_path / "src.zip"
    sha = make_zip(src, {bad: b"x"})
    with pytest.raises(A.AcquisitionError, match="unsafe"):
        A.acquire("t", spec_for(src, sha), tmp_path / "data")
    assert not (tmp_path / "evil.txt").exists()


def test_idempotent_second_run(tmp_path):
    src = tmp_path / "src.zip"
    sha = make_zip(src, {"a": b"1"})
    r1 = A.acquire("t", spec_for(src, sha), tmp_path / "data")
    r2 = A.acquire("t", spec_for(src, sha), tmp_path / "data")
    assert r1 == r2


def test_no_extract_verifies_only(tmp_path):
    src = tmp_path / "src.zip"
    sha = make_zip(src, {"a": b"1"})
    r = A.acquire("t", spec_for(src, sha), tmp_path / "data", extract=False)
    assert r["n_files"] == 0 and not (tmp_path / "data/ns/out").exists()


def test_real_manifest_is_wellformed():
    m = A.load_manifest(Path(__file__).parent.parent / "manifests" / "sources.json")
    for name, s in m.items():
        assert s["namespace"] == "cc-by-sa-4.0", name
        assert s["sha256"] is None or len(s["sha256"]) == 64
    assert all(s["sha256"] for s in m.values())
