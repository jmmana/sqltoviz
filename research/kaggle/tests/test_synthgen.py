import json

import numpy as np
import pytest

from sqltoviz_data import features as F
from sqltoviz_data import leakage as L
from sqltoviz_data import synthgen as G


@pytest.fixture(scope="module")
def items():
    return G.generate(120, seed=11)


def test_balanced_deterministic_and_schemas_class_agnostic(items):
    assert {c: sum(i["label"] == c for i in items) for c in G.BASE_CLASSES} == {c: 120 for c in G.BASE_CLASSES}
    again = G.generate(120, seed=11)
    assert json.dumps(items, sort_keys=True) == json.dumps(again, sort_keys=True)
    dense = G.generate(120, seed=11, n_schemas=30)             # ~40 items per schema
    from scipy.stats import chi2_contingency
    schemas = sorted({i["db_id"] for i in dense})
    table = [[sum(1 for i in dense if i["db_id"] == sc and i["label"] == c) for c in G.BASE_CLASSES] for sc in schemas]
    p = chi2_contingency(table)[1]
    assert p > 0.001, p        # schema and label independent: schema id carries no label information


def test_no_chart_vocabulary_anywhere(items):
    G.assert_no_chart_vocabulary(items)
    with pytest.raises(AssertionError):
        G.assert_no_chart_vocabulary([{"item_id": "x", "sql": "SELECT pie_total FROM t", "columns": ["pie"]}])


def test_every_item_extracts_under_frozen_contract(items):
    for i in items:
        t, c = F.extract(i["sql"], [{"name": n} for n in i["columns"]], i["rows"])
        assert np.isfinite(t).all() and np.isfinite(c).all()


@pytest.mark.parametrize("cls,check", [
    ("kpi", lambda i: len(i["rows"]) == 1),
    ("donut", lambda i: 2 <= len(i["rows"]) <= 5 and all(r[1] > 0 for r in i["rows"])),
    ("bar", lambda i: 6 <= len(i["rows"]) <= 15),
    ("horizontal_bar", lambda i: 8 <= len(i["rows"]) <= 25 and np.mean([len(r[0]) for r in i["rows"]]) > 20),
    ("heatmap", lambda i: len({r[0] for r in i["rows"]}) >= 6 and len({r[1] for r in i["rows"]}) >= 6
        and len(i["rows"]) == len({r[0] for r in i["rows"]}) * len({r[1] for r in i["rows"]})),
    ("stacked_bar", lambda i: 2 <= len({r[1] for r in i["rows"]}) <= 4),
    ("area", lambda i: all(r[1] >= 0 for r in i["rows"])),
    ("scatter", lambda i: len(i["rows"]) >= 30 and len(i["rows"][0]) == 2),
    ("table", lambda i: len(i["rows"][0]) >= 6),
])
def test_class_regimes_hold_by_construction(items, cls, check):
    sel = [i for i in items if i["label"] == cls]
    assert sel and all(check(i) for i in sel), cls


def test_label_not_recoverable_from_sql_beyond_structural_ceiling():
    """Class-agnostic templates: within a result shape, SQL-only / names-only models must be at chance."""
    items = G.generate(250, seed=5)
    rep = L.report(items, seed=0)
    ceil = rep["structural_ceiling_accuracy"]
    assert ceil == pytest.approx(0.6)
    for view in ("sql_features16", "sql_token_bag", "names_only"):
        v = rep["views"][view]
        assert v["accuracy"] <= ceil + 0.04, (view, v["accuracy"], ceil)
        for shape, w in v["within_shape"].items():
            assert w["accuracy"] <= w["chance"] + 0.09, (view, shape, w)
    # sanity: the data itself is informative (otherwise the generator would be meaningless)
    assert rep["views"]["data_features16_global"]["accuracy"] > 0.75
