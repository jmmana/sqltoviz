import numpy as np
import pytest

from sqltoviz_data import features as F
from sqltoviz_data import rules as R


def ex(sql, names, rows):
    return F.extract(sql, [{"name": n} for n in names], rows)


def test_kpi_and_wide_table():
    assert R.rule_predict(*ex("SELECT SUM(a) AS s FROM t", ["s"], [[10.0]])) == "kpi"
    wide = [[1, "a", 2.0, "x", 3.0, "y"]] * 20
    assert R.rule_predict(*ex("SELECT * FROM t", list("abcdef"), wide)) == "table"


def test_heatmap_vs_stacked_by_cardinality():
    big = [[f"a{i}", f"b{j}", float(i + j)] for i in range(6) for j in range(6)]
    small = [[f"a{i}", f"b{j}", float(i + j)] for i in range(4) for j in range(3)]
    assert R.rule_predict(*ex("SELECT a,b,SUM(v) FROM t GROUP BY a,b", ["a", "b", "v"], big)) == "heatmap"
    assert R.rule_predict(*ex("SELECT a,b,SUM(v) FROM t GROUP BY a,b", ["a", "b", "v"], small)) == "stacked_bar"


def test_line_area_scatter_donut_bars():
    days = [[f"2024-01-{d:02d}", float(d)] for d in range(1, 21)]
    assert R.rule_predict(*ex("SELECT d,SUM(v) FROM t GROUP BY d", ["d", "v"], days)) == "area"
    neg = [[f"2024-01-{d:02d}", float(d - 10)] for d in range(1, 21)]
    assert R.rule_predict(*ex("SELECT d,AVG(v) FROM t GROUP BY d", ["d", "v"], neg)) == "line"
    pts = [[float(i), float(i * 2 % 7)] for i in range(40)]
    assert R.rule_predict(*ex("SELECT x,y FROM t", ["x", "y"], pts)) == "scatter"
    assert R.rule_predict(*ex("SELECT c,SUM(v) FROM t GROUP BY c", ["c", "v"], [["a", 1.0], ["b", 2.0], ["c", 3.0]])) == "donut"
    many = [[f"cat{i}", float(i + 1)] for i in range(10)]
    assert R.rule_predict(*ex("SELECT c,SUM(v) FROM t GROUP BY c", ["c", "v"], many)) == "bar"
    longl = [[f"a very long category label number {i}", float(i + 1)] for i in range(10)]
    assert R.rule_predict(*ex("SELECT c,SUM(v) FROM t GROUP BY c", ["c", "v"], longl)) == "horizontal_bar"


def test_constraints_block_unsafe_and_fall_back():
    t, c = ex("SELECT c,SUM(v) FROM t GROUP BY c", ["c", "v"], [["a", -1.0], ["b", 2.0], ["c", 3.0]])
    el = R.eligible(t, c)
    assert not el["donut"] and not el["area"] and el["bar"] and el["table"]
    scores = np.zeros(10, dtype=np.float32)
    scores[R.CLASSES.index("donut")] = 0.9
    scores[R.CLASSES.index("bar")] = 0.1
    assert R.constrained_choice(scores, t, c) == ("bar", True)
    only_donut = np.zeros(10, dtype=np.float32)
    only_donut[R.CLASSES.index("kpi")] = 1
    assert R.constrained_choice(only_donut, t, c)[0] in R.CLASSES
    t1, c1 = ex("SELECT a FROM t", ["a"], [["x"]])      # nothing but table is safe
    assert [k for k, v in R.eligible(t1, c1).items() if v] == ["table"]
    assert R.constrained_choice(np.eye(10, dtype=np.float32)[0], t1, c1) == ("table", True)


def test_rules_return_valid_class_for_fuzz():
    import random
    rng = random.Random(0)
    for _ in range(60):
        M, N = rng.randint(1, 5), rng.randint(1, 30)
        rows = [[rng.choice([1.5, "a", None, "2024-01-01"]) for _ in range(M)] for _ in range(N)]
        t, c = ex("SELECT * FROM t", [f"c{j}" for j in range(M)], rows)
        assert R.rule_predict(t, c) in R.CLASSES
