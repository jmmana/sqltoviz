"""Golden parity fixtures for SDK implementations (Python, TypeScript, .NET).

Each fixture is (sql, schema, rows) plus either the expected features/scores or an expected rejection.
Fixtures are synthetic or hand-crafted only (no third-party corpus content), so they can be redistributed
under the project's Apache-2.0 license. Tolerance follows the contract: atol = rtol = 1e-6.
"""
from __future__ import annotations

import math
import random

import numpy as np

from . import features as F
from . import onnx_export as OX
from . import rules as RU

ATOL = RTOL = 1e-6


def handcrafted_cases() -> list:
    d = lambda name, sql, schema, rows, expect="accept": {"case_id": name, "sql": sql, "schema": schema, "rows": rows, "expect": expect, "kind": "handcrafted"}
    s = lambda *n: [{"name": x} for x in n]
    cs = []
    cs.append(d("kpi_single", "SELECT SUM(x) AS total FROM t", s("total"), [[10.5]]))
    cs.append(d("all_missing_column", "SELECT a, b FROM t", s("a", "b"), [[None, 1], [None, 2], ["", 3]]))
    cs.append(d("whitespace_string_is_value", "SELECT a FROM t", s("a"), [[" "], ["  "], ["x"]]))
    cs.append(d("nan_inf_missing", "SELECT v FROM t", s("v"), [[1.0], [float("nan")], [float("inf")], [None], [2.0]]))
    cs.append(d("negative_zero", "SELECT v FROM t", s("v"), [[-0.0], [0.0], [1.0]]))
    cs.append(d("boolean_column_nominal", "SELECT flag, n FROM t", s("flag", "n"), [[True, 1], [False, 2], [True, 3]]))
    cs.append(d("numeric_strings_nominal", "SELECT code FROM t", s("code"), [["1"], ["2"], ["3"]]))
    cs.append(d("unicode_names_and_values", "SELECT \"año\", país FROM t", s("año", "país"), [["2024", "México"], ["2025", "Perú"]]))
    cs.append(d("duplicate_column_names", "SELECT a, a FROM t", s("a", "a"), [[1, 2], [3, 4]]))
    cs.append(d("quoted_identifiers_and_comments", "/* c */ SELECT [a b], `c` FROM t -- end", s("a b", "c"), [[1, 2], [3, 4]]))
    cs.append(d("string_with_keywords", "SELECT 'JOIN GROUP BY; --' AS lit FROM t", s("lit"), [["x"]]))
    cs.append(d("zero_rows", "SELECT a FROM t", s("a"), []))
    cs.append(d("single_column_nominal", "SELECT name FROM t", s("name"), [["a"], ["b"], ["c"]]))
    cs.append(d("identifier_by_name", "SELECT user_id, score FROM t", s("user_id", "score"), [["u1", 1.0], ["u2", 2.0]]))
    cs.append(d("temporal_offsets", "SELECT ts, v FROM t ORDER BY ts", s("ts", "v"),
                [["2024-01-01T00:00:00Z", 1], ["2024-01-01T02:00:00+01:00", 2], ["2024-01-02T00:00:00.5Z", 3]]))
    cs.append(d("temporal_without_offset_is_nominal", "SELECT ts FROM t", s("ts"), [["2024-01-01T10:00:00"], ["2024-01-02T10:00:00"]]))
    cs.append(d("explicit_nominal_overrides_inference", "SELECT n FROM t", [{"name": "n", "type": "nominal"}], [[1], [2], [3]]))
    cs.append(d("explicit_identifier", "SELECT k FROM t", [{"name": "k", "type": "identifier"}], [[1], [2]]))
    cs.append(d("constant_quantitative", "SELECT v FROM t", s("v"), [[3.0]] * 6))
    cs.append(d("zero_mean_quantitative", "SELECT v FROM t", s("v"), [[-1.0], [1.0], [-2.0], [2.0]]))
    cs.append(d("crossed_2x3", "SELECT a,b,SUM(v) FROM t GROUP BY a,b", s("a", "b", "v"), [[a, b, float(i)] for i, (a, b) in enumerate((a, b) for a in "xy" for b in "pqr")]))
    cs.append(d("limit_top_forms", "SELECT TOP 10 a FROM t", s("a"), [[1], [2]]))
    cs.append(d("limit_non_literal", "SELECT a FROM t LIMIT ALL", s("a"), [[1]]))
    cs.append(d("cte_window_temporal_fn", "WITH c AS (SELECT strftime('%Y', d) y, v FROM t) SELECT y, SUM(v) OVER (ORDER BY y) FROM c", s("y", "v"), [["2024", 1], ["2025", 2]]))
    cs.append(d("calculated_projection", "SELECT a + b AS s, CASE WHEN a > 1 THEN 1 END AS c, -a AS n, t.* FROM t", s("s", "c", "n", "a", "b"), [[1, 2, 3, 4, 5]]))
    cs.append(d("group_by_ordinal_and_order_temporal", "SELECT d, SUM(v) FROM t GROUP BY 1 ORDER BY 1 ASC", s("d", "v"), [["2024-01-01", 1.0], ["2024-01-02", 2.0], ["2024-01-04", 5.0]]))
    cs.append(d("wide_128_columns", "SELECT * FROM t", s(*[f"c{i}" for i in range(128)]), [[float(i + j) for i in range(128)] for j in range(3)]))
    rj = lambda name, sql, schema, rows: d(name, sql, schema, rows, "reject")
    cs.append(rj("reject_unclosed_string", "SELECT 'abc FROM t", s("a"), [[1]]))
    cs.append(rj("reject_unclosed_comment", "SELECT 1 /* x", s("a"), [[1]]))
    cs.append(rj("reject_unclosed_bracket", "SELECT [a FROM t", s("a"), [[1]]))
    cs.append(rj("reject_nested_value", "SELECT a FROM t", s("a"), [[[1, 2]]]))
    cs.append(rj("reject_unsafe_integer", "SELECT a FROM t", s("a"), [[2 ** 60]]))
    cs.append(rj("reject_ragged_rows", "SELECT a, b FROM t", s("a", "b"), [[1, 2], [3]]))
    cs.append(rj("reject_129_columns", "SELECT * FROM t", s(*[f"c{i}" for i in range(129)]), [[0.0] * 129]))
    cs.append(rj("reject_zero_columns", "SELECT 1", [], []))
    cs.append(rj("reject_explicit_type_mismatch", "SELECT a FROM t", [{"name": "a", "type": "quantitative"}], [["x"]]))
    cs.append(rj("reject_explicit_temporal_mismatch", "SELECT a FROM t", [{"name": "a", "type": "temporal"}], [["2024-02-30"]]))
    cs.append(rj("reject_unknown_explicit_type", "SELECT a FROM t", [{"name": "a", "type": "bogus"}], [[1]]))
    return cs


def synthetic_cases(items: list, per_class: int, max_rows: int = 80, seed: int = 0) -> list:
    rng = random.Random(seed)
    out = []
    for cls in OX.CLASSES:
        pool = [i for i in items if i["label"] == cls and len(i["rows"]) <= max_rows]
        rng.shuffle(pool)
        for it in pool[:per_class]:
            out.append({"case_id": it["item_id"], "sql": it["sql"], "schema": [{"name": c} for c in it["columns"]], "rows": it["rows"],
                        "expect": "accept", "kind": "synthetic", "generator_label": cls})
    return out


def _clean(v):
    return None if isinstance(v, float) and not math.isfinite(v) else v


def build_golden(cases: list, sess=None, role_sess=None) -> dict:
    """Compute expected outputs with the reference implementation (+ ONNX session if given)."""
    out = []
    for c in cases:
        rec = {k: c[k] for k in ("case_id", "kind", "sql", "expect")}
        rec["schema"] = c["schema"]
        rec["rows"] = [[_clean(v) for v in r] if isinstance(r, list) else r for r in c["rows"]]
        if "generator_label" in c:
            rec["generator_label"] = c["generator_label"]
        try:
            t, cols = F.extract(c["sql"], c["schema"], c["rows"])
            if c["expect"] == "reject":
                raise AssertionError(f"{c['case_id']} expected rejection but was accepted")
            rec["expected"] = {"table_features": [float(x) for x in t], "column_features": [[float(x) for x in r] for r in cols]}
            if sess is not None:
                sc = OX.predict_onnx(sess, t[None, :])[0]
                rec["expected"]["chart_scores"] = [float(x) for x in sc]
                rec["expected"]["base_class"] = OX.CLASSES[int(np.argmax(sc))]
                final, changed = RU.constrained_choice(sc, t, cols)
                rec["expected"].update({"rule_class": RU.rule_predict(t, cols), "eligible": RU.eligible(t, cols),
                                        "final_class": final, "constraint_changed": bool(changed)})
            if role_sess is not None:
                rs = OX.predict_roles_onnx(role_sess, cols)
                rec["expected"]["role_scores"] = [[float(x) for x in r] for r in rs]
                rec["expected"]["roles"] = [OX.ROLES[int(np.argmax(r))] for r in rs]
        except F.FeatureError as e:
            if c["expect"] != "reject":
                raise
            rec["expected"] = {"rejected": True, "reason": str(e)}
        out.append(rec)
    return {"golden_version": 2, "contract_version": F.CONTRACT_VERSION, "contract_sha256": F.CONTRACT_SHA256, "atol": ATOL, "rtol": RTOL,
            "class_order": list(OX.CLASSES), "n_cases": len(out), "cases": out}


def verify_golden(g: dict, sess=None, role_sess=None) -> dict:
    """Re-run every case; report max abs diffs and failures."""
    fails, max_t, max_c, max_s, n_ok, n_rej = [], 0.0, 0.0, 0.0, 0, 0
    for c in g["cases"]:
        exp = c["expected"]
        try:
            t, cols = F.extract(c["sql"], c["schema"], c["rows"])
        except F.FeatureError:
            if exp.get("rejected"):
                n_rej += 1
            else:
                fails.append((c["case_id"], "unexpected rejection"))
            continue
        if exp.get("rejected"):
            fails.append((c["case_id"], "expected rejection"))
            continue
        et, ec = np.array(exp["table_features"], dtype=np.float32), np.array(exp["column_features"], dtype=np.float32)
        max_t, max_c = max(max_t, float(np.abs(t - et).max())), max(max_c, float(np.abs(cols - ec).max()))
        if not (np.allclose(t, et, atol=g["atol"], rtol=g["rtol"]) and np.allclose(cols, ec, atol=g["atol"], rtol=g["rtol"])):
            fails.append((c["case_id"], "feature mismatch"))
            continue
        if sess is not None and "chart_scores" in exp:
            sc = OX.predict_onnx(sess, t[None, :])[0]
            max_s = max(max_s, float(np.abs(sc - np.array(exp["chart_scores"])).max()))
            if not np.allclose(sc, exp["chart_scores"], atol=g["atol"], rtol=g["rtol"]):
                fails.append((c["case_id"], "score mismatch"))
                continue
            if "final_class" in exp:
                final, changed = RU.constrained_choice(sc, t, cols)
                if (final, bool(changed), RU.eligible(t, cols), RU.rule_predict(t, cols)) != (exp["final_class"], exp["constraint_changed"], exp["eligible"], exp["rule_class"]):
                    fails.append((c["case_id"], "classification mismatch"))
                    continue
        if role_sess is not None and "role_scores" in exp:
            rs = OX.predict_roles_onnx(role_sess, cols)
            if not np.allclose(rs, exp["role_scores"], atol=g["atol"], rtol=g["rtol"]) or [OX.ROLES[int(np.argmax(r))] for r in rs] != exp["roles"]:
                fails.append((c["case_id"], "role mismatch"))
                continue
        n_ok += 1
    return {"n_cases": len(g["cases"]), "accepted_ok": n_ok, "rejected_ok": n_rej, "failures": fails,
            "max_abs_diff": {"table_features": max_t, "column_features": max_c, "chart_scores": max_s}}
