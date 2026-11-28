import json

import pytest

from sqltoviz_data import llm_baseline as B


def item(i, **extra):
    return {"item_id": f"i{i}", "db_id": f"d{i % 3}", "sql": "SELECT a FROM t", "columns": ["a"], "rows": [[1], [2]], **extra}


def test_prompt_is_deterministic_blind_and_versioned():
    p = B.build_prompt(item(1))
    assert p == B.build_prompt(item(1)) and "SELECT a FROM t" in p and "table" in p and "Answer with JSON only" in p
    for banned in ("annotator", "claude", "codex", "synthetic", "consensus", "ground truth"):
        assert banned not in p.lower()
    with pytest.raises(ValueError):
        B.build_prompt(item(1, label="bar"))
    assert len(B.PROMPT_SHA256) == 64


def test_parser_is_strict_and_tolerates_wrapping():
    assert B.parse_response('Sure: {"primary": "bar", "acceptable": ["bar", "line", "pie"], "confidence": 2}')["acceptable"] == ["bar", "line"]
    assert B.parse_response('{"primary": "pie"}') is None and B.parse_response("no json") is None and B.parse_response("{bad json}") is None
    assert B.parse_response('{"primary": "table"}')["acceptable"] == ["table"]


def test_run_logs_everything_and_scores_with_failures_counted_as_errors():
    calls = []
    def fake(prompt):
        calls.append(prompt)
        return '{"primary": "table"}' if len(calls) % 2 else "I cannot decide"
    items = [item(i) for i in range(6)]
    recs = B.run(items, fake, "fake-model")
    assert [r.item_id for r in recs] == [f"i{i}" for i in range(6)] and all(r.prompt_sha256 == B.PROMPT_SHA256 for r in recs)
    truth = {f"i{i}": {"label": "table"} for i in range(6)}
    s = B.score(recs, truth, {f"i{i}": f"d{i % 3}" for i in range(6)}, reps=50)
    assert s["parse_failures"] == 3 and s["accuracy"] == pytest.approx(0.5) and s["majority_baseline"] == 1.0 and len(s["macro_f1_ci95_cluster_bootstrap"]) == 2


def test_score_only_uses_labelled_items():
    recs = B.run([item(0), item(1)], lambda p: '{"primary": "bar"}', "m")
    s = B.score(recs, {"i0": {"label": "bar", "acceptable": ["bar", "horizontal_bar"]}})
    assert s["n"] == 1 and s["accuracy"] == 1.0 and s["acceptable_hit_rate"] == 1.0
