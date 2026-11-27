"""Pipeline steps shared by the Kaggle notebooks (kept in a tested module so notebooks stay thin)."""
from __future__ import annotations

import glob
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from . import features as F
from . import sandbox as S

REAL_SOURCES = {
    "spider_train": lambda root: (f"{root}/spider/spider_data/train_spider.json", f"{root}/spider/spider_data/database", "query"),
    "spider_dev": lambda root: (f"{root}/spider/spider_data/dev.json", f"{root}/spider/spider_data/database", "query"),
    "bird_dev": lambda root: (f"{root}/bird_dev/dev_20240627/dev.json", None, "SQL"),
}


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def real_candidates(ns_root: str, sources=("spider_train", "spider_dev", "bird_dev"), max_per_source=None, timeout_s=10) -> tuple:
    """Execute gold queries in the sandbox; keep executable, non-empty, within-contract results."""
    items, stats = [], {}
    for src in sources:
        jf, dbdir, fld = REAL_SOURCES[src](ns_root)
        data = json.load(open(jf))
        if max_per_source:
            data = data[:max_per_source]
        c = {"input": len(data), "ok": 0, "not_executable": 0, "empty": 0, "out_of_contract": 0, "missing_db": 0}
        for i, ex in enumerate(data):
            db = ex["db_id"]
            p = f"{dbdir}/{db}/{db}.sqlite" if dbdir else next(iter(glob.glob(f"{ns_root}/bird_dev/**/dev_databases/{db}/{db}.sqlite", recursive=True)), None)
            if not p or not os.path.exists(p):
                c["missing_db"] += 1
                continue
            r = S.execute(p, ex[fld], timeout_s=timeout_s, max_rows=F.MAX_ROWS + 1)
            if r.status != "ok":
                c["not_executable"] += 1
            elif not r.rows:
                c["empty"] += 1
            elif r.truncated or len(r.columns) > F.MAX_COLUMNS:
                c["out_of_contract"] += 1
            else:
                c["ok"] += 1
                items.append({"item_id": f"{src}_{i}", "db_id": db, "sql": ex[fld], "columns": r.columns, "rows": r.rows, "source": src})
        stats[src] = c
    return items, stats


def save_features(path, items) -> dict:
    """Write contract features (table [n,32], columns concatenated [sum M,28] + offsets) to .npz."""
    tabs, cols, offs = [], [], [0]
    kept = []
    rejected = 0
    for it in items:
        try:
            t, c = F.extract(it["sql"], [{"name": n} for n in it["columns"]], it["rows"])
        except F.FeatureError:
            rejected += 1
            continue
        tabs.append(t)
        cols.append(c)
        offs.append(offs[-1] + len(c))
        kept.append(it["item_id"])
    np.savez_compressed(path, table=np.stack(tabs).astype(np.float32), columns=np.concatenate(cols).astype(np.float32),
                        offsets=np.array(offs, dtype=np.int64), item_ids=np.array(kept),
                        contract_version=F.CONTRACT_VERSION, contract_sha256=F.CONTRACT_SHA256)
    return {"n": len(kept), "rejected": rejected}


def load_features(path) -> dict:
    z = np.load(path, allow_pickle=False)
    if str(z["contract_sha256"]) != F.CONTRACT_SHA256:
        raise F.FeatureError("feature file was built with a different contract")
    offs = z["offsets"]
    return {"table": z["table"], "columns": [z["columns"][offs[i]:offs[i + 1]] for i in range(len(offs) - 1)],
            "item_ids": [str(x) for x in z["item_ids"]]}


def write_manifest(out_dir, files: dict, extra: dict) -> dict:
    """files: {relative_path: license_namespace}. Records sha256/size per file."""
    out_dir = Path(out_dir)
    entries = {rel: {"namespace": ns, "sha256": sha256_file(out_dir / rel), "bytes": (out_dir / rel).stat().st_size} for rel, ns in files.items()}
    prev = out_dir / "MANIFEST.json"
    if prev.exists():                                   # later notebooks add to (never overwrite) earlier entries
        old = json.loads(prev.read_text())
        if old.get("contract_sha256") != F.CONTRACT_SHA256:
            raise F.FeatureError("existing manifest was built with a different contract")
        entries = {**old.get("files", {}), **entries}
        extra = {**{k: v for k, v in old.items() if k not in ("files", "contract_version", "contract_sha256")}, **extra}
    man = {"contract_version": F.CONTRACT_VERSION, "contract_sha256": F.CONTRACT_SHA256, "files": entries, **extra}
    prev.write_text(json.dumps(man, indent=1, sort_keys=True))
    return man
