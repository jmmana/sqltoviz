import pytest

from sqltoviz_data import pilot as P
from sqltoviz_data.annotations import Annotation as A


def a(i, who, prim, acc=None, t="llm"):
    return A(i, who, t, prim, tuple(acc or (prim,)), 2)


def test_agreement_metrics_hand_values():
    x = [a("1", "A", "bar"), a("2", "A", "bar"), a("3", "A", "table"), a("4", "A", "table")]
    y = [a("1", "B", "bar"), a("2", "B", "table", ("table", "bar")), a("3", "B", "table"), a("4", "B", "table")]
    r = P.agreement_report(P.align(x, y))
    assert r["percent_agreement_primary"] == 0.75
    # po=.75; A: bar2 table2, B: bar1 table3 -> pe=(2*1+2*3)/16=.5 -> kappa=.5
    assert r["cohens_kappa_primary"] == pytest.approx(0.5)
    assert r["b_primary_in_a_acceptable"] == 0.75 and r["a_primary_in_b_acceptable"] == 1.0
    assert r["discrepancy_pairs"] == [{"a": "bar", "b": "table", "count": 1}]
    assert "NOT human" in r["note"]


def test_align_rejects_same_annotator_human_and_mismatch():
    x = [a("1", "A", "bar")]
    with pytest.raises(ValueError):
        P.align(x, [a("1", "A", "bar")])
    with pytest.raises(ValueError):
        P.align(x, [a("1", "B", "bar", t="human")])
    with pytest.raises(ValueError):
        P.align(x, [a("2", "B", "bar")])


def test_consensus_marks_source_and_leaves_disagreements_unlabeled():
    c = P.consensus_labels(P.align([a("1", "A", "bar"), a("2", "A", "bar")], [a("1", "B", "bar", ("bar", "horizontal_bar")), a("2", "B", "table")]))
    assert c["1"]["label_source"] == "llm_consensus" and c["1"]["label"] == "bar" and c["1"]["acceptable"] == ["bar", "horizontal_bar"]
    assert c["2"]["label"] is None and c["2"]["status"] == "disagree" and c["2"]["candidates"] == ["bar", "table"]
    assert all(v["label_source"] != "human" for v in c.values())


def test_stratified_reserve_size_coverage_determinism():
    strata = {f"i{k}": ("table" if k < 216 else "kpi" if k < 274 else "bar" if k < 296 else "horizontal_bar") for k in range(300)}
    r1 = P.stratified_reserve(strata, 100, seed=7)
    assert len(r1) == len(set(r1)) == 100
    assert r1 == P.stratified_reserve(dict(reversed(list(strata.items()))), 100, seed=7)
    from collections import Counter
    c = Counter(strata[i] for i in r1)
    assert c["horizontal_bar"] >= 1 and c["bar"] >= 1
    assert abs(c["table"] - 72) <= 2 and abs(c["kpi"] - 19.3) <= 2
    with pytest.raises(ValueError):
        P.stratified_reserve({"a": "x"}, 2, 0)
