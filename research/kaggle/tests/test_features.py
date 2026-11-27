"""Independent validation of the SqlVizSpec-v1.0.0 reference extractor.

References used (none share code with features.py): hand-derived values, numpy/scipy for the
statistics, and sqlglot's parser for lexical SQL features on real corpora (see tools/).
"""
import hashlib
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

from sqltoviz_data import features as F

ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT / "spec" / "sqlvizspec-v1-features.json"
T = {n["name"]: n["index"] for n in F.contract()["sql_features"]}
T.update({n["name"]: 16 + n["index"] for n in F.contract()["global_features"]})
C = {n["name"]: n["index"] for n in F.contract()["column_features"]}


def run(sql, schema, rows):
    t, c = F.extract(sql, [{"name": n} if isinstance(n, str) else n for n in schema], rows)
    return t, c


# ------------------------------------------------------------------ contract pin
def test_contract_pinned_and_verifier_passes():
    assert hashlib.sha256(SPEC.read_bytes()).hexdigest() == F.CONTRACT_SHA256
    r = subprocess.run([sys.executable, str(ROOT / "spec" / "verify_contract.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert F.CONTRACT_SHA256 in r.stdout
    assert len(F.contract()["sql_features"]) == 16 and len(F.contract()["global_features"]) == 16
    assert len(F.contract()["column_features"]) == 28


def test_tampered_contract_rejected(tmp_path):
    p = tmp_path / "c.json"
    p.write_bytes(SPEC.read_bytes() + b" ")
    with pytest.raises(F.FeatureError):
        F.load_contract(p)


def test_context_copies_align_with_table_indices():
    for name, src in [("context_group_by", "has_group_by"), ("context_temporal_order", "ascending_temporal_order"),
                      ("context_temporal_function", "has_temporal_function"), ("context_log_rows", "log_row_count"),
                      ("context_temporal_count", "temporal_count"), ("context_quantitative_count", "quantitative_count")]:
        d = [x for x in F.contract()["column_features"] if x["name"] == name][0]
        assert f"table_features[{T[src]}]" in d["formula"], name


# ------------------------------------------------------------------ hand-derived vector
def test_hand_derived_reference_case():
    sql = "SELECT dept, SUM(sal) AS total FROM emp GROUP BY dept ORDER BY 2 DESC LIMIT 5"
    t, c = run(sql, ["dept", "total"], [["a", 10], ["b", 20], ["c", 5]])
    # 20 tokens -> ln(21)
    assert t[T["log_token_count"]] == pytest.approx(math.log(21), rel=1e-6)
    assert t[T["join_count"]] == 0 and t[T["subquery_cte_count"]] == 0
    assert t[T["has_group_by"]] == 1 and t[T["group_expression_count"]] == 1
    assert t[T["has_order_by"]] == 1 and t[T["ascending_temporal_order"]] == 0
    assert t[T["has_limit"]] == 1 and t[T["normalized_limit"]] == pytest.approx(0.005)
    assert t[T["aggregate_count"]] == 1 and t[T["parenthesis_depth"]] == 1
    assert t[T["calculated_projection_ratio"]] == 0
    # globals: N=3 -> log10(4); small_rows; M=2; 1 nominal 1 quantitative
    assert t[T["log_row_count"]] == pytest.approx(math.log10(4), rel=1e-6)
    assert t[T["small_rows"]] == 1 and t[T["column_count"]] == 2 and t[T["quantitative_ratio"]] == 0.5
    assert t[T["non_null_density"]] == 1 and t[T["max_nominal_relative_cardinality"]] == 1
    assert t[T["min_nominal_cardinality"]] == 3 and t[T["mean_nominal_entropy"]] == pytest.approx(1.0)  # uniform over 3
    # column 1 (10,20,5): mu=35/3, population var = 350/9
    mu, var = 35 / 3, 350 / 9
    assert c[1, C["coefficient_of_variation"]] == pytest.approx(math.sqrt(var) / (mu + 1e-8), rel=1e-6)
    assert c[1, C["is_aggregated_in_sql"]] == 1 and c[0, C["is_aggregated_in_sql"]] == 0
    assert c[0, C["is_in_group_by"]] == 1 and c[1, C["is_in_group_by"]] == 0
    assert c[1, C["normalized_range"]] == pytest.approx(15 / (mu + 1e-8), rel=1e-6)
    # sorted 5,10,20: median 10, Q25=7.5, Q75=15 (type 7); MAD: |x-10| = 5,0,10 -> median 5
    assert c[1, C["normalized_iqr"]] == pytest.approx(7.5 / 10, rel=1e-6)
    assert c[1, C["normalized_mad"]] == pytest.approx(5 / 10, rel=1e-6)
    assert c[1, C["monotonicity"]] == pytest.approx(0.5)   # 10<=20 yes, 20<=5 no
    assert c[0, C["relative_position"]] == 0 and c[1, C["relative_position"]] == 1
    assert c[1, C["context_log_rows"]] == pytest.approx(math.log10(4), rel=1e-6)


def test_temporal_features_hand_derived():
    rows = [["2024-01-01"], ["2024-01-02"], ["2024-01-04"]]
    sql = "SELECT d FROM t ORDER BY d"
    t, c = run(sql, ["d"], rows)
    assert t[T["temporal_count"]] == 1 and t[T["ascending_temporal_order"]] == 1
    assert c[0, C["is_temporal"]] == 1
    # diffs 86400, 172800: mean 129600, population var 43200^2 -> var/mean^2 = 1/9
    assert c[0, C["temporal_step_irregularity"]] == pytest.approx(1 / 9, rel=1e-5)
    assert c[0, C["monotonicity"]] == 1
    t2, _ = run("SELECT d FROM t ORDER BY d DESC", ["d"], rows)
    assert t2[T["ascending_temporal_order"]] == 0
    t3, _ = run("SELECT d FROM t ORDER BY 1 ASC", ["d"], rows)
    assert t3[T["ascending_temporal_order"]] == 1


def test_crossed_structure():
    ok = [[a, b, i] for i, (a, b) in enumerate((a, b) for a in "xy" for b in "pqr")]
    sql = "SELECT a,b,v FROM t"
    sch = ["a", "b", "v"]
    assert run(sql, sch, ok)[0][T["crossed_structure"]] == 1
    miss = [r[:] for r in ok]
    miss[0][2] = None
    assert run(sql, sch, miss)[0][T["crossed_structure"]] == 0
    dup = ok + [ok[0][:]]
    assert run(sql, sch, dup)[0][T["crossed_structure"]] == 0
    assert run(sql, sch, ok[:-1])[0][T["crossed_structure"]] == 0   # N != K1*K2


# ------------------------------------------------------------------ numpy/scipy references
@pytest.mark.parametrize("seed", range(40))
def test_quantitative_statistics_match_numpy_scipy(seed):
    rng = np.random.default_rng(seed)
    n = int(rng.integers(3, 200))
    kind = seed % 4
    x = [rng.normal(5, 3, n), rng.lognormal(0, 1, n), rng.integers(-5, 50, n).astype(float), rng.exponential(2, n) - 1][kind]
    rows = [[float(v)] for v in x]
    _, c = run("SELECT v FROM t", ["v"], rows)
    mu, sd = x.mean(), x.std(ddof=0)
    exp = {
        "coefficient_of_variation": sd / (abs(mu) + 1e-8),
        "skewness": stats.skew(x, bias=True) * (sd ** 3) / (sd ** 3 + 1e-8) if sd > 0 else 0.0,
        "excess_kurtosis": (stats.kurtosis(x, fisher=False, bias=True) * sd ** 4) / (sd ** 4 + 1e-8) - 3 if sd > 0 else 0.0,
        "negative_ratio": float((x < 0).mean()),
        "zero_ratio": float((x == 0).mean()),
        "normalized_range": (x.max() - x.min()) / (abs(mu) + 1e-8),
        "normalized_iqr": (np.quantile(x, 0.75, method="linear") - np.quantile(x, 0.25, method="linear")) / (abs(np.median(x)) + 1e-8),
        "normalized_mad": np.median(np.abs(x - np.median(x))) / (abs(np.median(x)) + 1e-8),
        "monotonicity": float((np.diff(x) >= 0).mean()),
    }
    for k, v in exp.items():
        lo, hi = [d for d in F.contract()["column_features"] if d["name"] == k][0]["range"]
        v = min(max(float(v), lo), hi)
        assert c[0, C[k]] == pytest.approx(v, rel=2e-6, abs=2e-6), (k, seed)


def test_constant_and_degenerate_columns():
    _, c = run("SELECT v FROM t", ["v"], [[3.0]] * 5)
    assert c[0, C["skewness"]] == 0 and c[0, C["excess_kurtosis"]] == 0   # constant => 0 (not -3)
    assert c[0, C["coefficient_of_variation"]] == 0 and c[0, C["normalized_mad"]] == 0
    _, c1 = run("SELECT v FROM t", ["v"], [[3.0]])
    assert c1[0, C["monotonicity"]] == 0 and c1[0, C["normalized_range"]] == 0
    _, cz = run("SELECT v FROM t", ["v"], [[0.0], [0.0]])    # mu=0 -> epsilon denominators, finite
    assert np.isfinite(cz).all()


# ------------------------------------------------------------------ lexer
def test_lexer_opaque_strings_comments_and_rejection():
    sql = "SELECT 'a JOIN b; GROUP BY', \"x JOIN\" /* JOIN */ FROM t -- JOIN\n JOIN u ON 1=1"
    t, _ = run(sql, ["a", "b"], [[1, 2]])
    assert t[T["join_count"]] == 1 and t[T["has_group_by"]] == 0
    t, _ = run("SELECT 'it''s JOIN' FROM t", ["a"], [[1]])
    assert t[T["join_count"]] == 0
    for bad in ["SELECT 'abc", "SELECT \"abc", "SELECT 1 /* x", "SELECT [abc"]:
        with pytest.raises(F.FeatureError):
            F.lex(bad)


def test_case_insensitive_keywords_and_cte_subquery_counts():
    sql = "with c as (select a from t) select * from (select a from c) x join y on 1=1 left join z on 1=1"
    t, _ = run(sql, ["a"], [[1]])
    assert t[T["subquery_cte_count"]] == 2 and t[T["join_count"]] == 2


def test_limits_and_top():
    assert run("SELECT a FROM t LIMIT 5000", ["a"], [[1]])[0][T["normalized_limit"]] == 1
    assert run("SELECT a FROM t LIMIT 250", ["a"], [[1]])[0][T["normalized_limit"]] == pytest.approx(0.25)
    assert run("SELECT TOP 10 a FROM t", ["a"], [[1]])[0][T["normalized_limit"]] == pytest.approx(0.01)
    t, _ = run("SELECT a FROM t LIMIT ALL", ["a"], [[1]])
    assert t[T["has_limit"]] == 1 and t[T["normalized_limit"]] == 1
    t, _ = run("SELECT a FROM t", ["a"], [[1]])
    assert t[T["has_limit"]] == 0 and t[T["normalized_limit"]] == 1
    t, _ = run("SELECT a FROM (SELECT a FROM t LIMIT 5) q", ["a"], [[1]])
    assert t[T["has_limit"]] == 1 and t[T["normalized_limit"]] == 1    # inner LIMIT is not the outer one


def test_projection_ratio_window_temporal_having_distinct():
    t, _ = run("SELECT DISTINCT a+b AS s, c, CASE WHEN a>1 THEN 1 END, -a, t.* FROM t", ["s", "c", "k", "n", "x"], [[1, 2, 3, 4, 5]])
    assert t[T["calculated_projection_ratio"]] == pytest.approx(2 / 5)   # a+b and CASE; unary -a and t.* excluded
    assert t[T["has_distinct"]] == 1
    t, _ = run("SELECT strftime('%Y', d) y, row_number() over (partition by g order by d) FROM t HAVING 1=1", ["y", "r"], [[1, 2]])
    assert t[T["has_temporal_function"]] == 1 and t[T["has_window"]] == 1 and t[T["has_having"]] == 1
    t, _ = run("SELECT year FROM t", ["year"], [[1]])
    assert t[T["has_temporal_function"]] == 0      # YEAR not followed by '('
    t, _ = run("SELECT count(*), (SELECT max(x) FROM u) FROM t", ["a", "b"], [[1, 2]])
    assert t[T["aggregate_count"]] == 2            # max inside the outer projection counted once


def test_group_by_resolution():
    sch = ["dept", "total"]
    rows = [["a", 1]]
    _, c = run("SELECT dept, SUM(x) total FROM t GROUP BY 1", sch, rows)
    assert c[0, C["is_in_group_by"]] == 1 and c[1, C["is_in_group_by"]] == 0
    _, c = run("SELECT upper(dept) d, SUM(x) total FROM t GROUP BY upper(dept)", ["d", "total"], rows)
    assert c[0, C["is_in_group_by"]] == 1                    # exact projected expression
    _, c = run("SELECT a AS x, b AS a FROM t GROUP BY a", ["x", "a"], [[1, 2]])
    assert c[:, C["is_in_group_by"]].sum() == 0              # ambiguous => 0
    _, c = run("SELECT * FROM t GROUP BY a", ["a", "b"], [[1, 2]])
    assert c[:, C["is_in_group_by"]].sum() == 1              # name match still resolves 'a'
    _, c = run("SELECT * FROM t", ["a", "b"], [[1, 2]])
    assert c[:, C["is_aggregated_in_sql"]].sum() == 0        # unresolved projection


# ------------------------------------------------------------------ types and input rejection
def types_of(schema, rows):
    return [col.type for col in F.parse_input(schema, rows)]


def test_type_resolution():
    rows = [["2024-01-01", 1, "x", "u1", True, "1", "2024-01-01T10:00:00+02:00", None],
            ["2024-01-02", 2.5, "y", "u2", False, "2", "2024-01-01T10:00:00Z", None]]
    sch = [{"name": n} for n in ["d", "q", "n", "user_id", "b", "numstr", "ts", "empty"]]
    assert types_of(sch, rows) == ["temporal", "quantitative", "nominal", "identifier", "nominal", "nominal", "temporal", "nominal"]
    # temporal without explicit offset is NOT temporal; whitespace-only string is a valid (non-missing) value
    assert types_of([{"name": "t"}], [["2024-01-01T10:00:00"]]) == ["nominal"]
    c = F.Column("s", [" ", ""])
    assert c.n == 1 and c.type == "nominal"
    assert F.Column("q", [1, float("nan"), float("inf"), None]).n == 1
    assert F.Column("q", [-0.0, 0.0]).K == 1                 # negative zero normalized


def test_temporal_utc_seconds():
    assert F.parse_temporal("1970-01-01T00:00:00Z") == 0.0
    assert F.parse_temporal("1970-01-01T01:00:00+01:00") == 0.0
    assert F.parse_temporal("1970-01-01") == 0.0
    assert F.parse_temporal("2024-02-30") is None and F.parse_temporal("2024-13-01") is None
    assert F.parse_temporal("2024-01-01T00:00:00.5Z") == pytest.approx(1704067200.5)


def test_rejections():
    for rows, sch in [([[[1]]], [{"name": "a"}]),                        # nested
                      ([[2 ** 60]], [{"name": "a"}]),                    # unsafe integer
                      ([["x"]], [{"name": "a", "type": "quantitative"}]),
                      ([["x"]], [{"name": "a", "type": "temporal"}]),
                      ([[1]], [{"name": "a", "type": "bogus"}])]:
        with pytest.raises(F.FeatureError):
            F.parse_input(sch, rows)
    with pytest.raises(F.FeatureError):
        F.parse_input([{"name": "a"}], [[1, 2]])                          # ragged
    with pytest.raises(F.FeatureError):
        F.parse_input([{"name": str(i)} for i in range(129)], [[0] * 129])  # > max_columns
    with pytest.raises(F.FeatureError):
        F.parse_input([], [])


# ------------------------------------------------------------------ invariants
def test_fuzz_outputs_finite_in_range_and_float32():
    rng = random.Random(0)
    defs_t = F.contract()["sql_features"] + F.contract()["global_features"]
    defs_c = F.contract()["column_features"]
    for _ in range(150):
        M, N = rng.randint(1, 6), rng.randint(0, 60)
        sch, cols = [], []
        for j in range(M):
            k = rng.choice(["q", "n", "d", "id", "mix"])
            sch.append({"name": "id" if k == "id" else f"c{j}"})
            gen = {"q": lambda: rng.choice([rng.gauss(0, 100), None, 0, -3]),
                   "n": lambda: rng.choice(["a", "b", "c", None, ""]),
                   "d": lambda: rng.choice(["2024-01-01", "2024-03-05", None]),
                   "id": lambda: rng.choice([1, 2, 3]),
                   "mix": lambda: rng.choice([1, "a", None, True])}[k]
            cols.append(gen)
        rows = [[g() for g in cols] for _ in range(N)]
        sql = rng.choice(["SELECT * FROM t", "SELECT c0, SUM(c1) FROM t GROUP BY c0 ORDER BY 1 LIMIT 10",
                          "WITH a AS (SELECT 1) SELECT x FROM a JOIN b ON 1=1"])
        t, c = F.extract(sql, sch, rows)
        assert t.dtype == np.float32 and c.dtype == np.float32 and t.shape == (32,) and c.shape == (M, 28)
        assert np.isfinite(t).all() and np.isfinite(c).all()
        for v, d in zip(t, defs_t):
            assert d["range"][0] <= v <= d["range"][1]
        for row in c:
            for v, d in zip(row, defs_c):
                assert d["range"][0] <= v <= d["range"][1]


def test_extraction_is_deterministic():
    a = run("SELECT a FROM t ORDER BY a", ["a"], [[3], [1], [2]])
    b = run("SELECT a FROM t ORDER BY a", ["a"], [[3], [1], [2]])
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])


def test_interpretations_pin_matches_document_bytes():
    pin = F.interpretations_pin()
    doc = ROOT / "research" / "kaggle" / "FEATURE_INTERPRETATIONS.md"
    assert pin["sha256"] == hashlib.sha256(doc.read_bytes()).hexdigest()
    assert pin["file"].endswith("FEATURE_INTERPRETATIONS.md")


def test_lexical_ascii_only_for_digits_and_dates():
    """Non-ASCII digits must not lex as numbers or parse as dates (portability with JS/C#)."""
    assert [t.kind for t in F.lex("SELECT \u0663")] == ["word", "punct"]          # ARABIC-INDIC DIGIT THREE is not a number
    assert F.parse_temporal("\u0662\u0660\u0662\u0664-01-01") is None
    assert F.parse_temporal("2024-01-01\n") is None                                # no trailing newline tolerance


def test_whitespace_set_is_the_documented_unicode_set():
    ws = [0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x1C, 0x1D, 0x1E, 0x1F, 0x20, 0x85, 0xA0, 0x1680, *range(0x2000, 0x200B), 0x2028, 0x2029, 0x202F, 0x205F, 0x3000]
    assert [cp for cp in range(0x110000) if chr(cp).isspace()] == ws
