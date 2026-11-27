"""Blind human-validation workbook: build (no model/LLM information) and ingest (human labels, kept separate).

The evaluator workbook contains only: instructions, chart guide, and per case the SQL, result columns, a data preview and
empty answer cells. Case ids are neutral (H001...), shuffled with a seed; the id->item_id key is a SEPARATE file.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from .annotations import BASE_CLASSES, Annotation, AnnotationError

OTHER = "other (explain in observations)"
GUIDE = {
    "kpi": "One scalar metric (a single number or a metric with one comparison). Typically one row.",
    "bar": "Compare a measure across a moderate number of categories (vertical bars).",
    "horizontal_bar": "Ranking, or comparison with long category labels or many categories (horizontal bars).",
    "stacked_bar": "A measure split by two categorical dimensions where the parts add up (additive) and groups do not overlap.",
    "line": "A measure over an ordered temporal or sequential dimension.",
    "area": "Like a line, but the magnitude from a zero baseline is meaningful (volumes, cumulative amounts).",
    "donut": "Parts of a whole: a few mutually exclusive categories of a non-negative additive measure.",
    "scatter": "Relationship between two (or three) quantitative measures, one point per observation.",
    "heatmap": "Two categorical dimensions and one measure shown as a grid of cells.",
    "table": "No chart is justified: detail rows, text, identifiers, many mixed columns, or a chart would be misleading.",
}
INSTRUCTIONS_EN = [
    "SqlToViz - independent human validation of chart choices",
    "",
    "Goal: for each case, decide which visualization would be appropriate to show this query result to a person.",
    "You see the SQL query, the result columns and up to 20 result rows (a note says how many rows the full result has).",
    "",
    "For every case, fill (yellow columns):",
    "  1. Preferred chart: your single best choice (drop-down).",
    "  2. Valid alternatives: mark 'x' under every OTHER chart you consider acceptable (leave blank if none).",
    "  3. Confidence: 1 = low, 2 = medium, 3 = high.",
    "  4. Observations: anything unclear, misleading, or why you chose 'table' / 'other'.",
    "",
    "Rules:",
    "  - Judge only from the SQL and the data shown. Do not look anything up; do not use tools that suggest charts.",
    "  - If a chart would mislead (e.g. stacking values that are not additive, a donut of ratios), prefer 'table' or a safe alternative.",
    "  - Several charts can be valid: choose the best one as preferred and mark the rest as alternatives.",
    "  - If none of the 10 fits, choose 'other' and explain in Observations.",
    "  - Work alone and independently; do not discuss cases with other evaluators until all are finished.",
    "  - Do not edit the grey columns. Do not reorder rows. Save the file and return it.",
    "",
    "Instrucciones (resumen): para cada caso elige el gráfico preferido (lista desplegable), marca con 'x' las alternativas válidas,",
    "indica tu confianza (1-3) y escribe observaciones. Juzga solo con el SQL y los datos mostrados; trabaja de forma independiente.",
]


def _preview(columns, rows, max_rows=20, max_cell=40) -> str:
    def cell(v):
        s = "NULL" if v is None else str(v)
        return s if len(s) <= max_cell else s[: max_cell - 1] + "…"
    lines = [" | ".join(columns)]
    lines += [" | ".join(cell(v) for v in r) for r in rows[:max_rows]]
    return "\n".join(lines)[:30000]


def build_workbook(cases: list, out_xlsx, key_csv, seed: int = 20261127) -> list:
    """cases: dicts with item_id, sql, columns, rows. Returns the shuffled [(case_id, item_id)] key."""
    for c in cases:
        extra = set(c) - {"item_id", "sql", "columns", "rows", "db_id"}
        if extra:
            raise AnnotationError(f"case carries unexpected fields that may leak labels: {sorted(extra)}")
    order = sorted(cases, key=lambda c: c["item_id"])
    random.Random(seed).shuffle(order)
    key = [(f"H{k + 1:03d}", c["item_id"]) for k, c in enumerate(order)]
    wb = Workbook()
    ws = wb.active
    ws.title = "Instructions"
    for i, line in enumerate(INSTRUCTIONS_EN, 1):
        ws.cell(i, 1, line)
    ws["A1"].font = Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 130
    g = wb.create_sheet("Chart guide")
    g.append(["Chart", "When it is appropriate"])
    for k in BASE_CLASSES:
        g.append([k, GUIDE[k]])
    g.append([OTHER, "None of the ten options is suitable (explain in Observations)."])
    g.column_dimensions["A"].width = 32
    g.column_dimensions["B"].width = 120
    for c in g[1]:
        c.font = Font(bold=True)
    ws2 = wb.create_sheet("Cases")
    head = ["Case", "SQL query", "Result size", "Result columns and first rows", "Preferred chart (choose)"] + \
           [f"Alt: {k}" for k in BASE_CLASSES] + ["Confidence (1-3)", "Observations"]
    ws2.append(head)
    grey, yellow = PatternFill("solid", fgColor="E7E6E6"), PatternFill("solid", fgColor="FFF2CC")
    for c in ws2[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    by = {c["item_id"]: c for c in cases}
    for cid, iid in key:
        c = by[iid]
        n = len(c["rows"])
        ws2.append([cid, c["sql"], f"{n} row(s) x {len(c['columns'])} column(s)" + (" (preview shows first 20)" if n > 20 else ""),
                    _preview(c["columns"], c["rows"]), None] + [None] * len(BASE_CLASSES) + [None, None])
    last = ws2.max_row
    for row in ws2.iter_rows(min_row=2, max_row=last):
        for k, cell in enumerate(row):
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.fill = grey if k < 4 else yellow
    for col, w in zip("ABCD", (8, 55, 22, 70)):
        ws2.column_dimensions[col].width = w
    ws2.column_dimensions["E"].width = 30
    for j in range(len(BASE_CLASSES)):
        ws2.column_dimensions[chr(ord("F") + j)].width = 12
    ws2.column_dimensions["P"].width = 12
    ws2.column_dimensions["Q"].width = 45
    dv1 = DataValidation(type="list", formula1='"' + ",".join(list(BASE_CLASSES) + [OTHER]) + '"', allow_blank=True)
    dv2 = DataValidation(type="list", formula1='"x"', allow_blank=True)
    dv3 = DataValidation(type="list", formula1='"1,2,3"', allow_blank=True)
    for dv in (dv1, dv2, dv3):
        ws2.add_data_validation(dv)
    dv1.add(f"E2:E{last}")
    dv2.add(f"F2:O{last}")
    dv3.add(f"P2:P{last}")
    ws2.freeze_panes = "B2"
    wb.properties.creator = "SqlToViz"
    wb.save(out_xlsx)
    with open(key_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "item_id"])
        w.writerows(key)
    return key


def ingest(xlsx, key_csv, annotator_id: str) -> tuple:
    """Read a filled workbook -> (Annotations with annotator_type='human', list of problems)."""
    key = {r["case_id"]: r["item_id"] for r in csv.DictReader(open(key_csv))}
    ws = load_workbook(xlsx, data_only=True)["Cases"]
    hdr = [c.value for c in ws[1]]
    alt_cols = {k: hdr.index(f"Alt: {k}") for k in BASE_CLASSES}
    out, problems = [], []
    for row in ws.iter_rows(min_row=2, values_only=True):
        cid = row[0]
        if cid not in key:
            problems.append((cid, "unknown case id"))
            continue
        pref = row[4]
        if pref in (None, ""):
            problems.append((cid, "no preferred chart"))
            continue
        if pref == OTHER:
            problems.append((cid, "preferred=other (no base class)"))
            continue
        conf = row[hdr.index("Confidence (1-3)")]
        alts = {k for k, j in alt_cols.items() if str(row[j] or "").strip().lower() == "x"}
        try:
            out.append(Annotation(key[cid], annotator_id, "human", pref, tuple(sorted(alts | {pref})), int(conf) if conf else 2,
                                  str(row[hdr.index("Observations")] or "")))
            out[-1].validate()
        except (AnnotationError, ValueError) as e:
            problems.append((cid, str(e)))
            out.pop() if out and out[-1].item_id == key[cid] else None
    return out, problems
