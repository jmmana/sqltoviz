"""Reproducible, checksum-verified acquisition of public text-to-SQL corpora.

Fail-closed: a download whose size or SHA256 differs from the pinned manifest
is deleted and rejected. Sources with ``sha256: null`` are refused unless
``trust_on_first_use`` is set, in which case the observed hash is written to a
lock file that must be reviewed and committed.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

CHUNK = 1 << 20


class AcquisitionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def load_manifest(path: Path) -> dict:
    data = json.loads(Path(path).read_text())
    if data.get("manifest_version") != 1:
        raise AcquisitionError("unsupported manifest_version")
    return data["sources"]


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "sqltoviz-data/0.1"})
    with urllib.request.urlopen(req) as r, open(tmp, "wb") as out:  # noqa: S310
        shutil.copyfileobj(r, out, CHUNK)
    tmp.replace(dest)


def safe_extract(archive: Path, target: Path) -> list[str]:
    """Extract a zip, rejecting path traversal/absolute paths; skip __MACOSX."""
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            name = info.filename
            parts = PurePosixPath(name).parts
            if not parts or parts[0] == "__MACOSX":
                continue
            if name.startswith(("/", "\\")) or ".." in parts or (len(name) > 1 and name[1] == ":"):
                raise AcquisitionError(f"unsafe path in archive: {name!r}")
            dest = (target / name).resolve()
            if target != dest and target not in dest.parents:
                raise AcquisitionError(f"unsafe path in archive: {name!r}")
            if info.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out, CHUNK)
            extracted.append(name)
    return extracted


def acquire(name: str, spec: dict, root: Path, trust_on_first_use: bool = False) -> dict:
    """Download+verify+extract one source under ``root/<namespace>/``."""
    ns_dir = Path(root) / spec["namespace"]
    archive = ns_dir / "_downloads" / spec["filename"]
    pinned = spec.get("sha256")
    if pinned is None and not trust_on_first_use:
        raise AcquisitionError(f"{name}: sha256 not pinned; refusing (use trust_on_first_use and commit the lock)")
    if not archive.exists():
        download(spec["url"], archive)
    size = archive.stat().st_size
    if spec.get("size") is not None and size != spec["size"]:
        archive.unlink()
        raise AcquisitionError(f"{name}: size {size} != pinned {spec['size']}")
    digest = sha256_file(archive)
    if pinned is not None and digest != pinned:
        archive.unlink()
        raise AcquisitionError(f"{name}: sha256 {digest} != pinned {pinned}")
    out_dir = ns_dir / spec["extract_root"]
    files = safe_extract(archive, out_dir)
    for nested in spec.get("nested_archives", []):
        inner = out_dir / nested
        files += safe_extract(inner, inner.parent)
    return {"source": name, "namespace": spec["namespace"], "license": spec["license"],
            "sha256": digest, "size": size, "n_files": len(files), "pinned": pinned is not None}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--manifest", default=str(Path(__file__).parent.parent / "manifests" / "sources.json"))
    ap.add_argument("--root", default="data")
    ap.add_argument("--trust-on-first-use", action="store_true")
    ns = ap.parse_args(argv)
    manifest = load_manifest(Path(ns.manifest))
    lock = []
    for s in ns.sources:
        if s not in manifest:
            raise SystemExit(f"unknown source {s}")
        lock.append(acquire(s, manifest[s], Path(ns.root), ns.trust_on_first_use))
    print(json.dumps(lock, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
