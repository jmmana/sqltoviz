import csv

import pytest
from openpyxl import load_workbook

from sqltoviz_data import human_validation as H
from sqltoviz_data.annotations import AnnotationError


def cases(n=12):
    return [{"item_id": f"spider_train_{i}", "db_id": f"d{i % 3}", "sql": f"SELECT a FROM t{i}", "columns": ["a", "b"],
             "rows": [[j, f"x{j}"] for j in range(25)] if i % 2 else [[1, None]]} for i in range(n)]


def test_workbook_is_blind_shuffled_with_validations_and_separate_key(tmp_path):
    key = H.build_workbook(cases(), tmp_path / "w.xlsx", tmp_path / "key.csv", seed=1)
    wb = load_workbook(tmp_path / "w.xlsx")
    assert wb.sheetnames == ["Instructions", "Chart guide", "Cases"]
    ws = wb["Cases"]
    assert ws.max_row == 13 and [ws.cell(r, 1).value for r in range(2, 6)] == ["H001", "H002", "H003", "H004"]
    blob = " ".join(str(c.value).lower() for s in wb for row in s.iter_rows() for c in row if c.value)
    for banned in ("llm", "claude", "codex", "gpt", "synthetic", "prediction", "consensus", "spider_train", "stratum", "reserve"):
        assert banned not in blob, banned                       # no item ids, labels or provenance inside the evaluator file
    dvs = {tuple(dv.sqref.ranges)[0].coord: dv.formula1 for dv in ws.data_validations.dataValidation}
    assert any("kpi" in f and "other" in f for f in dvs.values()) and len(dvs) == 3
    assert "first 20" in ws.cell(2, 3).value or "first 20" in ws.cell(3, 3).value
    rows = list(csv.reader(open(tmp_path / "key.csv")))
    assert rows[0] == ["case_id", "item_id"] and len(rows) == 13 and [tuple(r) for r in rows[1:]] == key
    assert [k[1] for k in key] != sorted(k[1] for k in key)    # shuffled, not item order


def test_rejects_cases_with_extra_fields(tmp_path):
    bad = cases(2)
    bad[0]["label"] = "bar"
    with pytest.raises(AnnotationError):
        H.build_workbook(bad, tmp_path / "w.xlsx", tmp_path / "k.csv")


def test_ingest_roundtrip_and_problem_reporting(tmp_path):
    H.build_workbook(cases(6), tmp_path / "w.xlsx", tmp_path / "key.csv", seed=3)
    wb = load_workbook(tmp_path / "w.xlsx")
    ws = wb["Cases"]
    ws["E2"], ws["P2"], ws["F2"] = "table", 3, "x"                  # H001: preferred table, alt kpi, conf 3
    ws["E3"], ws["Q3"] = "bar", "ok"                                # H002: no confidence -> default 2
    ws["E4"] = H.OTHER                                              # H003: other -> problem
    # H004 left blank -> problem
    wb.save(tmp_path / "filled.xlsx")
    anns, problems = H.ingest(tmp_path / "filled.xlsx", tmp_path / "key.csv", "human-1")
    assert len(anns) == 2 and all(a.annotator_type == "human" for a in anns)
    a = next(a for a in anns if a.primary == "table")
    assert set(a.acceptable) == {"table", "kpi"} and a.confidence == 3
    assert {p[1] for p in problems} >= {"no preferred chart", "preferred=other (no base class)"}
