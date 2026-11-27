import random

import pytest

from sqltoviz_data import splits as S


def make(n_groups=40, per=12, classes=("bar", "line", "table", "kpi"), seed=1):
    rng = random.Random(seed)
    items = []
    for g in range(n_groups):
        for j in range(per):
            items.append({"item_id": f"g{g}_{j}", "db_id": f"db{g}", "sql": f"SELECT a{j} FROM t{g} WHERE x = {j}",
                          "label": rng.choice(classes)})
    return items


def test_normalization_collapses_literals_case_spacing():
    a = S.normalize_sql("SELECT  Name FROM t WHERE age > 30 AND city = 'Paris';")
    b = S.normalize_sql("select name from t where age > 99 and city = \"Rome\"")
    assert a == b
    assert S.sql_fingerprint("select 1") != S.sql_fingerprint("select a from t")


def test_dedup_within_group_only():
    items = [
        {"item_id": "1", "db_id": "A", "sql": "SELECT x FROM t WHERE a = 1"},
        {"item_id": "2", "db_id": "A", "sql": "select x from t where a = 2;"},     # near-dup of 1
        {"item_id": "3", "db_id": "B", "sql": "SELECT x FROM t WHERE a = 1"},     # same text, other schema: kept
        {"item_id": "4", "db_id": "A", "sql": "SELECT y FROM t"},
    ]
    kept, dropped, st = S.dedup(items)
    assert [k["item_id"] for k in kept] == ["1", "3", "4"]
    assert dropped == [{"item_id": "2", "duplicate_of": "1"}]
    assert st["cross_group_dup_templates"] == 1


def test_split_is_grouped_deterministic_and_audited():
    items = make()
    a1 = S.grouped_stratified_split(items, seed=3)
    a2 = S.grouped_stratified_split(list(reversed(items)), seed=3)
    assert a1 == a2
    rep = S.audit_splits(items, a1)
    n = rep["n"]
    for s, r in zip(("train", "val", "test"), (0.7, 0.15, 0.15)):
        assert abs(rep["splits"][s]["n"] / n - r) < 0.08, rep["splits"][s]
    assert {s for s in a1.values()} == {"train", "val", "test"}


def test_split_class_balance_tracks_global():
    items = make(n_groups=80, per=10)
    a = S.grouped_stratified_split(items, seed=0)
    rep = S.audit_splits(items, a)
    glob = {c: sum(1 for i in items if i["label"] == c) / len(items) for c in ("bar", "line", "table", "kpi")}
    for s in ("train", "val", "test"):
        tot = rep["splits"][s]["n"]
        for c, p in glob.items():
            assert abs(rep["splits"][s]["classes"].get(c, 0) / tot - p) < 0.12, (s, c)


def test_audit_detects_group_leak_and_missing():
    items = make(n_groups=5, per=4)
    a = S.grouped_stratified_split(items, seed=0)
    bad = dict(a)
    victim = items[0]["item_id"]
    bad[victim] = "test" if a[victim] != "test" else "train"
    with pytest.raises(AssertionError, match="groups spanning"):
        S.audit_splits(items, bad)
    with pytest.raises(AssertionError, match="cover"):
        S.audit_splits(items, {k: v for k, v in a.items() if k != victim})


def test_bad_ratios():
    with pytest.raises(ValueError):
        S.grouped_stratified_split(make(2, 2), ratios=(0.5, 0.5, 0.5))
