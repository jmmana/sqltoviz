#!/usr/bin/env python3
"""Differential fuzz cases for cross-runtime parity. Expected values come from the Python SDK (stdlib only).
Usage: python parity/tools/gen_fuzz.py OUT.json [N=3000] [SEED=20261127]
TypeScript and .NET test suites replay the file when SQLTOVIZ_FUZZ=OUT.json is set (CI always does)."""
import json, math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages" / "python"))
from sqltoviz import features as F

out, n, seed = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3000, int(sys.argv[3]) if len(sys.argv) > 3 else 20261127
rng = random.Random(seed)
WORDS = ["alpha", "beta", "gamma", "Δelta", "日本", "x y", " ", "O'Brien", "a;b", "emoji😀", "é", "", "UPPER", "lower", "0123", "true", "2024-01-01", "1e3"]
NAMES = ["id", "user_id", "ID", "uuid", "ref_ID", "day", "d", "amount", "v", "value", "cat", "region", "name", "Total", "x", "y", "a b", "año"]


def maybe_missing(v, p=0.1):
    r = rng.random()
    return None if r < p / 2 else (float("nan") if r < p * 0.7 else ("" if r < p else v))


def col_values(style, N):
    if style == "q":
        scale = 10.0 ** rng.randint(-7, 9); kind = rng.random()
        gen = (lambda: rng.randint(-50, 5000)) if kind < 0.3 else (lambda: round(rng.gauss(0, 1) * scale, rng.choice([0, 2, 6]))) if kind < 0.8 else (lambda: rng.choice([0.1, 0.2, 0.3, 0, -0.0, 1e-9]))
    elif style == "n":
        pool = rng.sample(WORDS, rng.randint(1, len(WORDS)))
        gen = lambda: rng.choice(pool)
    elif style == "d":
        valid = ["2024-01-05", "2024-03-10", "2020-02-29", "2024-03-11T00:00:00Z", "2024-04-01T12:00:00+01:00", "2023-12-31T23:59:59.250-02:00", "1999-12-31"]
        invalid = ["2024-02-30", "2024-1-1", "garbage", "2024-01-01T10:00:00", "2023-02-29", "2024-01-01T24:00:00Z"]
        p_inv = rng.choice([0, 0, 0, 0.1, 0.5])
        gen = lambda: rng.choice(invalid) if rng.random() < p_inv else rng.choice(valid)
    elif style == "b":
        gen = lambda: rng.choice([True, False])
    elif style == "mix":
        gen = lambda: rng.choice([1, "a", 2.5, True, None, "", "2024-01-01"])
    elif style == "idint":
        gen = lambda: rng.randint(1, 30)
    elif style == "bigint":
        gen = lambda: rng.choice([2 ** 53 - 1, -(2 ** 53 - 1), 1, 2 ** 60]) if rng.random() < 0.02 else rng.randint(0, 100)
    else:  # all missing
        gen = lambda: rng.choice([None, ""])
    return [maybe_missing(gen(), rng.choice([0, 0, 0.05, 0.3])) if style != "allmiss" else gen() for _ in range(N)]


TEMPLATES = [
    "SELECT {c0}, SUM({c1}) AS {c1} FROM t GROUP BY {c0}", "SELECT {c0}, {c1} FROM t ORDER BY {c0}", "SELECT {c0}, {c1} FROM t ORDER BY 1 DESC LIMIT 10",
    "SELECT * FROM t", "SELECT DISTINCT {c0} FROM t WHERE {c1} > 5", "SELECT COUNT(*) FROM t", "WITH c AS (SELECT {c0}, {c1} FROM t) SELECT {c0}, AVG({c1}) FROM c GROUP BY 1 ORDER BY 1",
    "SELECT a.{c0}, b.{c1} FROM t a JOIN u b ON a.id = b.id LEFT JOIN w ON 1=1", "SELECT {c0}, ROW_NUMBER() OVER (PARTITION BY {c1} ORDER BY {c0}) FROM t",
    "SELECT strftime('%Y', {c0}) AS y, {c1} FROM t GROUP BY y HAVING COUNT(*) > 1", "SELECT TOP 5 {c0} FROM t", "SELECT {c0} + {c1} AS s, -{c0}, CASE WHEN {c0} > 1 THEN 1 END FROM t",
    "SELECT \"{c0}\", [{c1}] FROM t /* c; JOIN */ ORDER BY \"{c0}\" ASC", "SELECT {c0} FROM (SELECT {c0} FROM t LIMIT 5) q LIMIT 20", "SELECT upper({c0}), COUNT(*) FROM t GROUP BY UPPER({c0})",
    "SELECT {c0}, {c1} FROM t -- trailing JOIN\nORDER BY {c1} DESC, {c0}", "SELECT 'a;b', {c0} FROM t UNION SELECT 'c', {c1} FROM u ORDER BY 1", "SELECT DATE_TRUNC('month', {c0}) AS m, SUM({c1}) FROM t GROUP BY 1 ORDER BY m",
    "SELECT {c0}, {c1} FROM t LIMIT 5, 10", "SELECT {c0} FROM t LIMIT ALL", "SELECT {c0} FROM t WHERE x IN (SELECT y FROM u WHERE z = ((1+2)*3))", "SELECT t.*, {c0} FROM t",
    "SELECT {c0} FROM t WHERE name = 'unclosed", "SELECT {c0} FROM t /* unclosed", "SELECT [{c0} FROM t", "select  {c0},\t{c1} from t group by 1,2",
]
cases = []
for k in range(n):
    M, N = rng.randint(1, 8), rng.choice([0, 1, 2, 3, 5, 12, 40, 80, rng.randint(0, 200)])
    styles = [rng.choice(["q", "q", "n", "n", "d", "b", "mix", "idint", "allmiss", "bigint"]) for _ in range(M)]
    names = [rng.choice(NAMES) for _ in range(M)]
    if rng.random() < 0.4: names = [f"{nm}{j}" if j else nm for j, nm in enumerate(names)] if rng.random() < 0.5 else names
    cols = [col_values(s, N) for s in styles]
    schema = [{"name": nm} for nm in names]
    for j, s in enumerate(styles):                       # sometimes force an explicit type (valid or not)
        if rng.random() < 0.05: schema[j]["type"] = rng.choice(["temporal", "quantitative", "nominal", "identifier", "bogus"])
    rows = [[cols[j][i] for j in range(M)] for i in range(N)]
    if rng.random() < 0.01 and rows: rows[0] = rows[0][:-1]          # ragged
    sql = rng.choice(TEMPLATES).format(c0=names[0], c1=names[min(1, M - 1)])
    case = {"case_id": f"fuzz_{seed}_{k}", "sql": sql, "schema": schema, "rows": [[None if (isinstance(v, float) and not math.isfinite(v)) else v for v in r] for r in rows]}
    try:
        t, c = F.extract(sql, schema, rows)
        case["expected"] = {"table_features": t, "column_features": c}
    except F.FeatureError:
        case["expected"] = {"rejected": True}
    cases.append(case)
json.dump({"seed": seed, "n": n, "atol": 1e-6, "rtol": 1e-6, "cases": cases}, open(out, "w"))
rej = sum(1 for c in cases if c["expected"].get("rejected"))
print(f"{n} cases, {rej} expected rejections, {n - rej} accepted -> {out}")
