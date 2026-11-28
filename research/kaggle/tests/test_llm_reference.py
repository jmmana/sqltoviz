import json
from pathlib import Path

import pytest

from sqltoviz_data import confirmatory as C, llm_baseline as B, llm_reference as L

K = Path(__file__).resolve().parent.parent


def test_real_annotator_files_load_and_are_all_non_human():
    ann = L.load_annotators(K)
    assert set(ann) == set(L.ANNOTATORS) and all(len(v) == 100 for v in ann.values())
    for f in ("claude_labels_reserved100.jsonl", "ai_workbook_labels_reserved100.jsonl"):
        assert all(json.loads(l)["human"] is False for l in open(K / "annotations" / f))


def test_reference_ties_are_listed_not_guessed():
    ann = {a: {"x": {"primary": p, "acceptable": [p]}, "y": {"primary": "table", "acceptable": ["table"]}}
           for a, p in zip(L.ANNOTATORS, ("bar", "bar", "kpi", "kpi"))}
    r = L.reference(ann)
    assert r["unresolved"] == ["x"] and list(r["truth"]) == ["y"] and r["votes_strength"] == {4: 1}


def test_llm_reference_provenance_is_never_confirmatory_or_human():
    assert C.LLM_REF in C.TIERS and "no human validation" in C.BANNER[C.LLM_REF]
    with pytest.raises(ValueError):
        C.write_report({"provenance": C.LLM_REF, "confirmatory": True}, Path("/tmp/x.json"))


def test_committed_report_declares_design():
    p = K / "reports" / "llm_reference_reserved100.json"
    if p.exists():
        d = json.loads(p.read_text())
        assert d["provenance"] == "llm_reference" and d["confirmatory"] is False and d["human_validation"].startswith("none")


def test_recommender_replay_scores_logged_responses():
    items = [{"item_id": "a", "db_id": "d1", "sql": "select 1", "columns": ["c"], "rows": [[1]]}]
    recs = B.run(items, lambda p: '{"primary":"kpi"}', "stub")
    s = B.score(recs, {"a": {"label": "kpi"}})
    assert s["accuracy"] == 1.0 and s["parse_failures"] == 0
