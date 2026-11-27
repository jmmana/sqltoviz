import pytest

from sqltoviz_data import annotations as A


def ann(i, who, prim, typ="human", acc=None, conf=3):
    return A.Annotation(i, who, typ, prim, tuple(acc or (prim,)), conf)


def test_validation():
    with pytest.raises(A.AnnotationError):
        ann("1", "a", "pie").validate()
    with pytest.raises(A.AnnotationError):
        A.Annotation("1", "a", "human", "bar", ("line",), 3).validate()
    with pytest.raises(A.AnnotationError):
        A.Annotation("1", "a", "robot", "bar", ("bar",), 3).validate()
    with pytest.raises(A.AnnotationError):
        A.Annotation("1", "a", "human", "bar", ("bar",), 5).validate()
    A.Annotation.from_dict({"item_id": "1", "annotator_id": "a", "annotator_type": "human", "primary": "bar", "confidence": 2})


def test_rule_labels_not_ground_truth_and_duplicates():
    with pytest.raises(A.AnnotationError):
        A.validate_for_ground_truth([ann("1", "r", "bar", typ="rule")])
    with pytest.raises(A.AnnotationError):
        A.validate_for_ground_truth([ann("1", "a", "bar"), ann("1", "a", "line")])


def test_cohen_kappa_known_values():
    assert A.cohen_kappa(list("aabb"), list("aabb")) == 1.0
    x = ["y"] * 25 + ["n"] * 25
    y = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15   # po=0.7 pe=0.5 -> 0.4
    assert A.cohen_kappa(x, y) == pytest.approx(0.4, abs=1e-9)
    assert A.cohen_kappa(list("abab"), list("baba")) == pytest.approx(-1.0)


def test_krippendorff_perfect():
    same = [ann(str(i), w, "bar" if i % 2 else "line") for i in range(10) for w in "AB"]
    assert A.krippendorff_alpha_nominal(same) == pytest.approx(1.0)


def test_krippendorff_exact_small():
    # units: AA, AA, AB, BB; do=2, n=8, nA=5, nB=3 -> alpha = 1 - 7*2/(2*5*3)
    anns = [ann("1", "x", "bar"), ann("1", "y", "bar"), ann("2", "x", "bar"), ann("2", "y", "bar"),
            ann("3", "x", "bar"), ann("3", "y", "line"), ann("4", "x", "line"), ann("4", "y", "line")]
    assert A.krippendorff_alpha_nominal(anns) == pytest.approx(1 - 14 / 30)


def test_adjudication_statuses():
    anns = [ann("1", "a", "bar"), ann("1", "b", "bar"), ann("1", "c", "line"),
            ann("2", "a", "bar"), ann("2", "b", "line"),
            ann("3", "a", "bar"), ann("4", "a", "bar"), ann("4", "b", "bar")]
    r = A.adjudicate(anns)
    assert r["1"]["label"] == "bar" and r["1"]["status"] == "majority"
    assert r["2"]["status"] == "tie_needs_adjudication" and r["2"]["label"] is None
    assert r["3"]["status"] == "insufficient_annotators"
    assert r["4"]["status"] == "unanimous"


def test_blind_pack_rejects_leaks_and_is_deterministic():
    good = [{"item_id": f"s{i}", "db_id": f"db{i % 3}", "sql": "select 1", "columns": ["a"], "rows_preview": [[1]]} for i in range(30)]
    p1 = A.build_task_pack(good, 12, seed=7)
    p2 = A.build_task_pack(list(reversed(good)), 12, seed=7)
    assert [x["item_id"] for x in p1] == [x["item_id"] for x in p2]
    assert len({x["db_id"] for x in p1}) == 3 and len(p1) == 12
    with pytest.raises(A.AnnotationError):
        A.build_task_pack([dict(good[0], chart_type="bar")], 1, seed=1)
