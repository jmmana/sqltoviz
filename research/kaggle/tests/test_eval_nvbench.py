import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import eval_nvbench as N  # noqa: E402

REPO = Path(__file__).resolve().parents[3]


def test_mapping_is_explicit_and_complete():
    assert N.VIS_MAP == {"Bar": "bar", "Stacked Bar": "stacked_bar", "Pie": "donut", "Line": "line", "Grouping Line": "line",
                         "Scatter": "scatter", "Grouping Scatter": "scatter"}
    assert N.map_vis_type("Grouping Line") == "line" and N.map_vis_type("Grouping Scatter") == "scatter" and N.map_vis_type("Pie") == "donut"
    assert N.map_vis_type("Heatmap") is None   # unknown types are dropped, never guessed


def test_mapping_targets_are_base_classes_and_cover_five():
    from sqltoviz._contract import BASE_CLASSES
    assert set(N.VIS_MAP.values()) <= set(BASE_CLASSES) and set(N.VIS_MAP.values()) == set(N.COVERED) and len(N.COVERED) == 5


def test_chart_data_rows_long_format():
    cols, rows = N.chart_data_rows({"x_name": "r", "y_name": "n", "x_data": [["a", "b"]], "y_data": [[1, 2], [3, 4]], "classify": ["F", "M"]})
    assert cols == ["r", "n", "series"] and rows == [["a", 1, "F"], ["b", 2, "F"], ["a", 3, "M"], ["b", 4, "M"]]


def test_evaluate_metrics_and_provenance_free_of_rows():
    y = ["bar"] * 6 + ["line"] * 6
    g = ["a", "a", "b", "b", "c", "c"] * 2
    preds = {"p": list(y), "always_bar": ["bar"] * 12}
    r = N.evaluate(y, preds, g, {"p": [[t, "x"] for t in y]}, reps=50)
    assert r["systems"]["p"]["accuracy"] == 1 and r["systems"]["p"]["macro_f1_covered"] == 1 and r["systems"]["p"]["top2_accuracy"] == 1
    assert r["systems"]["always_bar"]["accuracy"] == 0.5 and r["systems"]["always_bar"]["top2_accuracy"] is None
    assert r["macro_f1_classes"] == ["bar", "line"] and r["bootstrap"]["n_clusters"] == 3


def test_no_nvbench_files_tracked_by_git():
    assert N.tracked_nvbench_files(REPO) == []


def test_guard_detects_tracked_nvbench(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "NVBench.json").write_text("{}")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-f", "NVBench.json"], check=True)
    assert N.tracked_nvbench_files(tmp_path) == ["NVBench.json"]


def test_committed_report_has_provenance_and_no_item_data():
    p = REPO / "research/kaggle/reports/nvbench_eval.json"
    if not p.exists():
        pytest.skip("report not generated")
    d = json.loads(p.read_text())
    assert d["provenance"] == "external_human_authored_nvbench" and d["confirmatory"] is False
    assert d["nvbench"]["sha256"] == N.NVBENCH_SHA256 and d["contract_sha256"] and d["models"]["chart"]["sha256"] and d["models"]["role"]["sha256"]
    txt = p.read_text().lower()
    assert "select " not in txt and "nl_queries" not in txt
