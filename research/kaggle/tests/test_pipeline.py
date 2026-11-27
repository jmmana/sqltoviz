import json
import sqlite3

import numpy as np
import pytest

from sqltoviz_data import features as F
from sqltoviz_data import pipeline as P


def mk_spider(tmp_path):
    root = tmp_path / "ns"
    db = root / "spider/spider_data/database/d1"
    db.mkdir(parents=True)
    c = sqlite3.connect(db / "d1.sqlite")
    c.execute("create table t(a int, b text)")
    c.executemany("insert into t values(?,?)", [(i, f"x{i}") for i in range(5)])
    c.commit(); c.close()
    qs = [{"db_id": "d1", "query": q} for q in ["SELECT a, b FROM t", "SELECT count(*) FROM t", "SELECT a FROM t WHERE a > 99", "DROP TABLE t", "SELECT nope FROM t"]]
    json.dump(qs, open(root / "spider/spider_data/dev.json", "w"))
    return str(root)


def test_real_candidates_filters_and_counts(tmp_path):
    items, st = P.real_candidates(mk_spider(tmp_path), sources=("spider_dev",))
    assert st["spider_dev"] == {"input": 5, "ok": 2, "not_executable": 2, "empty": 1, "out_of_contract": 0, "missing_db": 0}
    assert [i["item_id"] for i in items] == ["spider_dev_0", "spider_dev_1"]


def test_feature_file_roundtrip_and_contract_guard(tmp_path):
    items = [{"item_id": "a", "sql": "SELECT a FROM t", "columns": ["a"], "rows": [[1], [2]]},
             {"item_id": "b", "sql": "SELECT a, b FROM t", "columns": ["a", "b"], "rows": [[1, "x"]]},
             {"item_id": "bad", "sql": "SELECT 'x FROM t", "columns": ["a"], "rows": [[1]]}]
    st = P.save_features(tmp_path / "f.npz", items)
    assert st == {"n": 2, "rejected": 1}
    d = P.load_features(tmp_path / "f.npz")
    assert d["table"].shape == (2, 32) and [c.shape for c in d["columns"]] == [(1, 28), (2, 28)] and d["item_ids"] == ["a", "b"]
    z = dict(np.load(tmp_path / "f.npz"))
    z["contract_sha256"] = np.array("0" * 64)
    np.savez(tmp_path / "g.npz", **z)
    with pytest.raises(F.FeatureError):
        P.load_features(tmp_path / "g.npz")


def test_manifest_hashes(tmp_path):
    (tmp_path / "x.txt").write_text("hi")
    m = P.write_manifest(tmp_path, {"x.txt": "apache-2.0"}, {"seed": 1})
    assert m["files"]["x.txt"]["sha256"] == P.sha256_file(tmp_path / "x.txt") and m["contract_sha256"] == F.CONTRACT_SHA256
    assert json.loads((tmp_path / "MANIFEST.json").read_text())["seed"] == 1
