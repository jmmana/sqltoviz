"""Synthetic (SQL, result set, base-class label) generator without label leakage.

Design:
* **Label by construction from the result data**, never from the SQL: each class has a data
  generator (shape, cardinality, value process). Gaps between class regimes avoid ambiguous
  zones. This encodes *our* convention for prototypical cases - it is not human preference
  (documented limitation; see SYNTHETIC_DATA.md).
* **Schemas are class-agnostic**: ``schema_id`` families draw table/column names from shared
  vocabularies; any class can be produced from any schema, so grouping splits by schema is leak-free.
* **SQL templates are sampled per *shape*, independent of class** within a shape (bar, horizontal_bar and
  donut share the same templates; line/area share theirs; stacked_bar/heatmap share theirs).
* No chart vocabulary may appear in SQL text, identifiers or aliases (`FORBIDDEN_WORDS`, asserted).
Residual dependence of SQL on label through shape (e.g. scalar queries have no GROUP BY) is natural
and is *measured* by ``leakage.py``, not denied.
"""
from __future__ import annotations

import math
import random
import re
from datetime import date, timedelta

BASE_CLASSES = ("kpi", "bar", "horizontal_bar", "stacked_bar", "line", "area", "donut", "scatter", "heatmap", "table")
FORBIDDEN_WORDS = ("bar", "pie", "donut", "line", "area", "chart", "plot", "kpi", "heatmap", "heat", "scatter", "stack",
                   "stacked", "table", "gauge", "graph", "viz", "visual", "metric", "trend")
ACCEPTABLE = {  # classes that are also reasonable for the generated data (used for lenient scoring only)
    "bar": ("bar", "horizontal_bar"), "horizontal_bar": ("horizontal_bar", "bar"), "donut": ("donut", "bar"),
    "line": ("line", "area"), "area": ("area", "line"), "stacked_bar": ("stacked_bar",), "heatmap": ("heatmap",),
    "kpi": ("kpi",), "scatter": ("scatter",), "table": ("table",),
}

ENTITIES = "orders customers products invoices shipments employees tickets sessions payments accounts visits claims loans devices readings events listings bookings students courses patients samples vehicles parcels stores suppliers contracts campaigns".split()
DIMS = "region segment channel status category department country brand tier plan carrier priority type source team warehouse grade branch industry owner method stage".split()
MEASURES = "revenue cost quantity amount duration score weight price units balance volume rating margin latency spend discount tax distance count_value".split()
TIMES = "created_at order_date event_date booked_on paid_on logged_at ship_date opened_on".split()
WORDS = "alpha harbor summit meadow quartz lantern copper willow harvest granite ember coastal northern central eastern western urban rural digital premium standard basic express regional global".split()
LONG = ("international wholesale distribution partners", "enterprise customer success management", "northwest regional logistics hub",
        "commercial refrigeration equipment sales", "independent software licensing resellers", "municipal infrastructure services group",
        "precision manufacturing and tooling division", "consumer electronics retail operations")


def _leak_free(name: str) -> bool:
    low = name.lower()
    return not any(w in re.split(r"[^a-z]+", low) for w in FORBIDDEN_WORDS)


def make_schema(schema_id: int, seed: int) -> dict:
    r = random.Random(f"{seed}:schema:{schema_id}")
    pick = lambda pool, k: r.sample(pool, k)
    s = {"schema_id": f"syn_{schema_id:04d}", "table": r.choice(ENTITIES), "table2": r.choice(ENTITIES),
         "dims": pick(DIMS, 3), "measures": pick(MEASURES, 4), "time": r.choice(TIMES), "id": r.choice(["id", "order_id", "ref_id", "uid"])}
    for v in [s["table"], s["table2"], s["time"], s["id"], *s["dims"], *s["measures"]]:
        assert _leak_free(v), v
    return s


# ----------------------------------------------------------------------------- data generators
def _labels(r, k, long=False):
    out = set()
    while len(out) < k:
        if long:
            out.add(r.choice(LONG) + f" {r.choice(WORDS)} {r.randint(1, 999)}")
        else:
            out.add(f"{r.choice(WORDS)}{r.randint(1, 99)}"[:12])
    return sorted(out)


def _dates(r, n, step):
    d0 = date(2018, 1, 1) + timedelta(days=r.randint(0, 900))
    if step == "month":
        out = []
        y, m = d0.year, d0.month
        for _ in range(n):
            out.append(date(y, m, 1))
            m += 1
            if m > 12:
                y, m = y + 1, 1
        return [d.isoformat() for d in out]
    days = {"day": 1, "week": 7}[step]
    return [(d0 + timedelta(days=days * i)).isoformat() for i in range(n)]


def gen_data(cls: str, r: random.Random) -> dict:
    """Return {shape, names:[roles], rows:[[...]]} for a class (roles guide SQL template naming)."""
    pos = lambda mu, sg: max(0.01, r.lognormvariate(mu, sg))
    if cls == "kpi":
        m = r.choice([1, 1, 2])
        return {"shape": "scalar", "rows": [[round(pos(5, 1.5), 2) for _ in range(m)]], "ncols": m}
    if cls in ("bar", "donut", "horizontal_bar"):
        k = {"bar": r.randint(6, 15), "donut": r.randint(2, 5), "horizontal_bar": r.randint(8, 25)}[cls]
        labs = _labels(r, k, long=(cls == "horizontal_bar"))
        vals = [round(pos(4, 0.9), 2) for _ in range(k)]
        if cls == "bar" and r.random() < 0.3:
            vals = [round(v - r.uniform(0, 40), 2) for v in vals]
        rows = [[l, v] for l, v in zip(labs, vals)]
        if r.random() < 0.5:   # sortedness identical across bar/horizontal_bar/donut (no ORDER BY leak)
            rows.sort(key=lambda x: -x[1])
        return {"shape": "cat_quant", "rows": rows}
    if cls in ("stacked_bar", "heatmap"):
        k1, k2 = (r.randint(3, 10), r.randint(2, 4)) if cls == "stacked_bar" else (r.randint(6, 15), r.randint(6, 15))
        a, b = _labels(r, k1), _labels(r, k2)
        rows = [[x, y, round(pos(3, 0.8), 2)] for x in a for y in b]
        if cls == "stacked_bar" and r.random() < 0.3:      # sparse series, still disjoint pairs
            rows = [row for row in rows if r.random() > 0.15] or rows
        return {"shape": "two_nom_quant", "rows": rows}
    if cls in ("line", "area"):
        n, step = r.randint(12, 120), r.choice(["day", "week", "month"])
        ds = _dates(r, n, step)
        if cls == "area":                                      # non-negative magnitude, zero baseline
            lvl, vals = pos(4, 0.5), []
            cum = r.random() < 0.5
            acc = 0.0
            for _ in range(n):
                v = lvl * (0.6 + 0.8 * r.random())
                acc += v
                vals.append(round(acc if cum else v, 2))
        else:                                                  # level far from zero or sign-changing process
            lvl, vals, x = r.uniform(-30, 120), [], 0.0
            for _ in range(n):
                x += r.gauss(0, 6)
                vals.append(round(lvl + x, 2))
            if min(vals) >= 0 and r.random() < 0.7:            # enforce a non-zero baseline for positive series
                vals = [round(v + 200, 2) for v in vals]
        return {"shape": "time_quant", "rows": [[d, v] for d, v in zip(ds, vals)]}
    if cls == "scatter":
        n, rho = r.randint(30, 300), r.uniform(-0.9, 0.9)
        rows = []
        for _ in range(n):
            u, w = r.gauss(0, 1), r.gauss(0, 1)
            rows.append([round(50 + 10 * u, 2), round(20 + 5 * (rho * u + math.sqrt(1 - rho * rho) * w), 2)])
        return {"shape": "quant_quant", "rows": rows}
    if cls == "table":
        m, n = r.randint(6, 10), r.randint(5, 200)
        kinds = [r.choice(["nom", "quant", "id", "time", "nom", "quant"]) for _ in range(m)]
        pool = _labels(r, 30)
        rows = []
        for i in range(n):
            row = []
            for k in kinds:
                row.append({"nom": lambda: r.choice(pool), "quant": lambda: round(r.gauss(100, 40), 2),
                            "id": lambda: i + 1, "time": lambda: (date(2020, 1, 1) + timedelta(days=r.randint(0, 700))).isoformat()}[k]())
            rows.append(row)
        return {"shape": "wide", "rows": rows, "kinds": kinds}
    raise ValueError(cls)


# ----------------------------------------------------------------------------- SQL templates (per shape, class-agnostic)
def make_sql(shape: str, data: dict, s: dict, r: random.Random) -> tuple:
    """Returns (sql, column_names). Template choice is independent of the class label."""
    t, t2, ident = s["table"], s["table2"], s["id"]
    d1, d2, d3 = s["dims"]
    m1, m2, m3, m4 = s["measures"]
    tm = s["time"]
    alias = lambda: r.choice(["total", "value", "amount", "result", "n", "sum_v", "avg_v"])
    n = r.choice([0, 5, 10, 100])
    if shape == "scalar":
        k = data["ncols"]
        a, b = "total", "peak"
        opts = [(f"SELECT SUM({m1}) AS {a} FROM {t}", [a]), (f"SELECT COUNT(*) AS {a} FROM {t} WHERE {m2} > {n}", [a]),
                (f"SELECT AVG({m1}) AS {a} FROM {t}", [a])]
        two = [(f"SELECT AVG({m1}) AS {a}, MAX({m1}) AS {b} FROM {t}", [a, b]), (f"SELECT SUM({m1}) AS {a}, SUM({m2}) AS {b} FROM {t}", [a, b])]
        return r.choice(opts if k == 1 else two)
    if shape == "cat_quant":
        a = alias()
        agg = r.choice(["SUM", "AVG", "MAX"])
        has_desc = data["rows"][0][1] >= data["rows"][-1][1] and len(data["rows"]) > 1
        order = f" ORDER BY {a} DESC" if has_desc and r.random() < 0.6 else ""
        opts = [f"SELECT {d1}, {agg}({m1}) AS {a} FROM {t} GROUP BY {d1}{order}",
                f"SELECT {d1}, COUNT(*) AS {a} FROM {t} GROUP BY 1{order}",
                f"SELECT x.{d1}, {agg}(y.{m1}) AS {a} FROM {t} x JOIN {t2} y ON x.{ident} = y.{ident} GROUP BY x.{d1}{order}",
                f"SELECT {d1}, {agg}({m2}) AS {a} FROM {t} WHERE {m2} > {n} GROUP BY {d1} HAVING COUNT(*) > {r.choice([0, 1, 3])}{order}",
                f"SELECT {d1}, {agg}({m1}) / {r.choice([1, 100])} AS {a} FROM {t} GROUP BY {d1}{order}"]
        return r.choice(opts), [d1, a]
    if shape == "two_nom_quant":
        a = alias()
        opts = [f"SELECT {d1}, {d2}, SUM({m1}) AS {a} FROM {t} GROUP BY {d1}, {d2}",
                f"SELECT {d1}, {d2}, SUM({m1}) AS {a} FROM {t} GROUP BY 1, 2 ORDER BY 1, 2",
                f"SELECT {d1}, {d2}, COUNT(*) AS {a} FROM {t} WHERE {m2} > {n} GROUP BY {d1}, {d2}",
                f"SELECT x.{d1}, x.{d2}, AVG(y.{m1}) AS {a} FROM {t} x JOIN {t2} y ON x.{ident} = y.{ident} GROUP BY x.{d1}, x.{d2}"]
        return r.choice(opts), [d1, d2, a]
    if shape == "time_quant":
        a, p = alias(), r.choice(["period", "day", "bucket"])
        opts = [(f"SELECT {tm}, SUM({m1}) AS {a} FROM {t} GROUP BY {tm} ORDER BY {tm}", [tm, a]),
                (f"SELECT strftime('%Y-%m-%d', {tm}) AS {p}, AVG({m1}) AS {a} FROM {t} GROUP BY 1 ORDER BY 1", [p, a]),
                (f"SELECT {tm}, SUM(SUM({m1})) OVER (ORDER BY {tm}) AS {a} FROM {t} GROUP BY {tm}", [tm, a]),
                (f"SELECT DATE_TRUNC('day', {tm}) AS {p}, COUNT(*) AS {a} FROM {t} WHERE {m2} > {n} GROUP BY 1 ORDER BY 1", [p, a]),
                (f"SELECT {tm}, MAX({m1}) AS {a} FROM {t} GROUP BY {tm}", [tm, a])]
        return r.choice(opts)
    if shape == "quant_quant":
        opts = [(f"SELECT {m1}, {m2} FROM {t}", [m1, m2]), (f"SELECT {m1}, {m2} FROM {t} WHERE {m1} IS NOT NULL", [m1, m2]),
                (f"SELECT AVG({m1}) AS x_v, AVG({m2}) AS y_v FROM {t} GROUP BY {ident}", ["x_v", "y_v"]),
                (f"SELECT {m1}, {m2} FROM {t} WHERE {m3} > {n} ORDER BY {m1}", [m1, m2])]
        return r.choice(opts)
    if shape == "wide":
        pool = [d1, d2, d3, m1, m2, m3, m4, tm, ident, f"{t}_ref"]
        r.shuffle(pool)
        cols = pool[:len(data["kinds"])]          # same naming vocabulary as every other class
        sel = ", ".join(cols)
        opts = [f"SELECT * FROM {t}", f"SELECT {sel} FROM {t} ORDER BY {cols[0]}", f"SELECT {sel} FROM {t} WHERE {m1} > {n}"]
        return r.choice(opts), cols
    raise ValueError(shape)


def generate(n_per_class: int, seed: int, n_schemas: int = 300) -> list:
    r = random.Random(seed)
    schemas = [make_schema(i, seed) for i in range(n_schemas)]
    items = []
    for cls in BASE_CLASSES:
        for i in range(n_per_class):
            s = r.choice(schemas)
            data = gen_data(cls, r)
            sql, names = make_sql(data["shape"], data, s, r)
            items.append({"item_id": f"syn_{seed}_{cls}_{i}", "db_id": s["schema_id"], "sql": sql, "columns": names,
                          "rows": data["rows"], "label": cls, "acceptable": list(ACCEPTABLE[cls]), "source": "synthetic"})
    r.shuffle(items)
    return items


def assert_no_chart_vocabulary(items: list) -> None:
    """Fail if chart words appear as whole words in SQL identifiers/aliases (keywords like COUNT are not chart words)."""
    for it in items:
        words = set(re.split(r"[^a-z]+", it["sql"].lower()))
        bad = words & set(FORBIDDEN_WORDS)
        # 'line'/'area' etc. never appear in templates; 'table' not used; flag anything left
        assert not bad, (it["item_id"], bad, it["sql"])
        assert all(_leak_free(c) for c in it["columns"]), (it["item_id"], it["columns"])
