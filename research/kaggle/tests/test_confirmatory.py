import json

import pytest

from sqltoviz_data import confirmatory as C
from sqltoviz_data import synthgen as G


def test_resolve_truth_majority_ties_and_single_annotator():
    rows = [{"item_id": "a", "primary": "bar", "acceptable": ["bar"]}, {"item_id": "a", "primary": "bar", "acceptable": ["bar", "line"]},
            {"item_id": "b", "primary": "bar", "acceptable": ["bar"]}, {"item_id": "b", "primary": "line", "acceptable": ["line"]},
            {"item_id": "c", "primary": "kpi", "acceptable": ["kpi"]}]
    r = C.resolve_truth(rows)
    assert r["truth"]["a"]["label"] == "bar" and r["truth"]["a"]["acceptable"] == ["bar", "line"]
    assert r["unresolved"] == ["b"] and r["single_annotator"] == ["c"] and "b" not in r["truth"]


def test_low_support_classes_excluded_from_macro_f1():
    labels, excl = C.supported_classes(["table"] * 7 + ["bar"] * 5 + ["kpi"] * 4)
    assert labels == ["bar", "table"] and excl == {"kpi": 4}


def test_paired_bootstrap_reports_all_pairs_and_detects_a_real_gap():
    y = (["bar", "table"] * 30)
    good, bad = list(y), ["table"] * 60
    out = C.paired_cluster_bootstrap(y, {"good": good, "bad": bad, "same": list(y)}, [f"g{i // 2}" for i in range(60)], ["bar", "table"], reps=200)
    assert len(out["pairwise"]) == 3
    assert out["pairwise"]["good - bad"]["excludes_zero"] and not out["pairwise"]["good - same"]["excludes_zero"]


def test_write_report_guards(tmp_path):
    fake = {"provenance": C.FAKE, "confirmatory": False}
    with pytest.raises(ValueError):
        C.write_report(fake, tmp_path / "result.json")                       # FAKE needs a FAKE name
    with pytest.raises(ValueError):
        C.write_report(fake, tmp_path / "reports" / "FAKE_x.json")           # and never inside reports/
    with pytest.raises(ValueError):
        C.write_report({"provenance": C.LLM, "confirmatory": True}, tmp_path / "x.json")
    with pytest.raises(ValueError):
        C.write_report({"provenance": C.SYNTHETIC, "confirmatory": False}, tmp_path / "FAKE_x.json")
    assert C.write_report({"provenance": C.HUMAN, "confirmatory": True}, tmp_path / "ok.json").exists()
    assert C.write_report(fake, tmp_path / "FAKE_ok.json").exists()


def test_analyze_tiers_carry_provenance_and_never_claim_confirmatory():
    items = G.generate(40, seed=5, n_schemas=40)
    tr, te = items[: len(items) * 2 // 3], items[len(items) * 2 // 3:]
    tr = [i for i in tr if i["db_id"] not in {t["db_id"] for t in te}] or tr
    rep = C.analyze(tr, te, {i["item_id"]: {"label": i["label"]} for i in te}, C.SYNTHETIC, reps=50)
    assert rep["provenance"] == "synthetic" and rep["confirmatory"] is False and "exploratory" in rep["banner"]
    assert set(rep["systems"]) >= {"rules", "hybrid_semantic"} and rep["systems"]["hybrid_semantic"]["semantic_violation_rate"] == 0
    assert rep["paired_cluster_bootstrap"] and "always_table" in rep["paired_cluster_bootstrap"]["macro_f1_ci95"]
    with pytest.raises(ValueError):
        C.analyze(tr, te, {}, C.SYNTHETIC)
    with pytest.raises(ValueError):
        C.analyze(tr, te, {"x": {"label": "bar"}}, "made-up")


def test_fake_dry_run_end_to_end_is_marked_fake_and_isolated(tmp_path):
    rep = C.fake_dry_run(tmp_path, n_cases=30, reps=30)
    assert rep["provenance"] == "FAKE_DRYRUN" and rep["confirmatory"] is False and "FAKE" in rep["banner"] and "FAKE" in rep["warning"]
    assert all(p.name.startswith("FAKE") for p in tmp_path.iterdir())
    assert rep["n_test"] + rep["n_without_truth"] == 30 and rep["n_test"] >= 10
    p = C.write_report(rep, tmp_path / "FAKE_report.json")
    assert json.loads(p.read_text())["provenance"] == "FAKE_DRYRUN"
