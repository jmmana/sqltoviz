import numpy as np
import pytest

from sqltoviz_data import experiment as E
from sqltoviz_data import splits as S
from sqltoviz_data import synthgen as G


@pytest.fixture(scope="module")
def result():
    items = G.generate(60, seed=3, n_schemas=60)
    assign = S.grouped_stratified_split(items, group=lambda x: x["db_id"], seed=1)
    tr = [i for i in items if assign[i["item_id"]] == "train"]
    te = [i for i in items if assign[i["item_id"]] == "test"]
    assert not {i["db_id"] for i in tr} & {i["db_id"] for i in te}       # no schema shared across train/test
    return E.evaluate_all(tr, te, seed=0), tr, te


def test_all_five_systems_reported_with_required_metrics(result):
    res, tr, te = result
    assert set(res["systems"]) == set(E.SYSTEMS)
    for s, m in res["systems"].items():
        assert 0 <= m["accuracy"] <= 1 and 0 <= m["macro_f1"] <= 1 and len(m["macro_f1_ci95_cluster_bootstrap"]) == 2
        assert sum(v["support"] for v in m["per_class"].values()) == len(te)
        assert 0 <= m["semantic_violation_rate"] <= 1 and "acceptable_hit_rate" in m
        assert np.array(m["confusion_matrix"]["matrix"]).sum() == len(te)


def test_semantic_constraints_never_violate_and_hybrid_beats_single_views_on_synthetic(result):
    res, *_ = result
    assert res["systems"]["hybrid_semantic"]["semantic_violation_rate"] == 0
    assert res["systems"]["hybrid"]["macro_f1"] >= res["systems"]["sql_only"]["macro_f1"]
    assert res["systems"]["data_only"]["macro_f1"] > res["majority_baseline"]["accuracy"]


def test_meta_records_contract_pin():
    m = E.run_meta({"seed": 1})
    assert m["contract_version"] == "SqlVizSpec-v1.0.0"
    assert m["contract_sha256"] == "d14d140b9118c0b535d4e504af7f16546f47d56ac8f1692c2ab62615686e5864" and m["seed"] == 1


def test_item_hash_is_order_independent():
    a = G.generate(5, seed=1, n_schemas=5)
    assert E.sha256_items(a) == E.sha256_items(list(reversed(a)))


def test_ablation_groups_partition_and_report(result):
    res, tr, te = result
    Xtr, _ = E.featurize(tr)
    Xte, _ = E.featurize(te)
    ab = E.ablate(Xtr, [i["label"] for i in tr], Xte, [i["label"] for i in te], seed=0)
    assert set(ab["groups"]) == set(E.ABLATION_GROUPS) and 0 <= ab["full"] <= 1
    assert sum(g["n_features"] for g in ab["groups"].values()) == 32
