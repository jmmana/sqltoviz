"""LLM-as-recommender baseline harness (#93): versioned prompt, strict parser, reproducible logging and scoring.

No model is called here: ``run`` takes an injected ``call(prompt) -> str`` so the same harness works with any provider and with replayed
responses. Every record stores the model id, prompt hash and the exact response, so a run can be audited and re-scored offline.
Scoring uses ONLY labels of a stated provenance (human for confirmatory use); LLM-vs-LLM agreement is never reported as accuracy."""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from dataclasses import dataclass

import numpy as np
from sklearn.metrics import f1_score

from .annotations import BASE_CLASSES

PROMPT_VERSION = "llm-baseline-v1"
DEFINITIONS = {
    "kpi": "one scalar metric (single row)", "bar": "compare a measure across a moderate number of categories",
    "horizontal_bar": "ranking or long/many category labels", "stacked_bar": "measure split by two categorical dimensions, additive parts",
    "line": "measure over an ordered temporal/sequential dimension", "area": "like line but magnitude from a zero baseline matters",
    "donut": "parts of a whole: few exclusive categories, non-negative additive measure", "scatter": "relationship between two quantitative measures",
    "heatmap": "two categorical dimensions and one measure as a grid", "table": "no chart is justified or a chart would mislead"}
TEMPLATE = """You recommend a visualization for a SQL query result. Choose exactly one primary class from: {classes}.
Definitions:
{definitions}
Judge only from the SQL, the columns and the rows shown (at most {max_rows}; the full result has {n_rows} rows). If a chart would be misleading, answer table.
SQL:
{sql}
Columns: {columns}
Rows:
{rows}
Answer with JSON only: {{"primary": "<class>", "acceptable": ["<class>", ...], "confidence": 1|2|3}}"""
PROMPT_SHA256 = hashlib.sha256((PROMPT_VERSION + TEMPLATE + json.dumps(DEFINITIONS, sort_keys=True)).encode()).hexdigest()


def build_prompt(item: dict, max_rows: int = 20) -> str:
    """item: sql, columns, rows. Contains no labels, scores or other annotators' answers by construction."""
    extra = set(item) - {"item_id", "db_id", "sql", "columns", "rows"}
    if extra:
        raise ValueError(f"item carries unexpected fields {sorted(extra)}")
    rows = "\n".join(" | ".join("NULL" if v is None else str(v)[:40] for v in r) for r in item["rows"][:max_rows])
    return TEMPLATE.format(classes=", ".join(BASE_CLASSES), definitions="\n".join(f"- {k}: {v}" for k, v in DEFINITIONS.items()),
                           max_rows=max_rows, n_rows=len(item["rows"]), sql=item["sql"], columns=", ".join(item["columns"]), rows=rows)


def parse_response(text: str) -> dict | None:
    """Strict: the first JSON object in the text must have a valid primary class; unknown acceptable classes are dropped; otherwise None."""
    s, e = text.find("{"), text.rfind("}")
    if s < 0 or e < s:
        return None
    try:
        d = json.loads(text[s:e + 1])
    except ValueError:
        return None
    if not isinstance(d, dict) or d.get("primary") not in BASE_CLASSES:
        return None
    acc = [c for c in (d.get("acceptable") or [d["primary"]]) if c in BASE_CLASSES]
    return {"primary": d["primary"], "acceptable": sorted(set(acc) | {d["primary"]}), "confidence": d.get("confidence") if d.get("confidence") in (1, 2, 3) else None}


@dataclass
class RunRecord:
    item_id: str
    model: str
    prompt_version: str
    prompt_sha256: str
    response: str
    parsed: dict | None


def run(items: list, call, model: str) -> list:
    """Query ``call`` once per item (deterministic order). Parse failures are kept (parsed=None), never silently replaced."""
    return [RunRecord(it["item_id"], model, PROMPT_VERSION, PROMPT_SHA256, (resp := call(build_prompt(it))), parse_response(resp))
            for it in sorted(items, key=lambda x: x["item_id"])]


def score(records: list, truth: dict, groups: dict | None = None, reps: int = 1000, seed: int = 0) -> dict:
    """truth: item_id -> {'label': class, 'acceptable': [...] (optional)} from ONE named provenance. Parse failures count as errors (predicted 'table' is NOT assumed)."""
    ids = [r.item_id for r in records if r.item_id in truth]
    pred = {r.item_id: (r.parsed or {}).get("primary") for r in records}
    y = [truth[i]["label"] for i in ids]
    p = [pred[i] or "<unparsed>" for i in ids]
    labels = [c for c in BASE_CLASSES if c in set(y)]
    acc_hit = [pred[i] in set(truth[i].get("acceptable") or [truth[i]["label"]]) for i in ids]
    out = {"n": len(ids), "parse_failures": sum(1 for i in ids if pred[i] is None), "accuracy": float(np.mean([a == b for a, b in zip(y, p)])),
           "macro_f1": float(f1_score(y, p, labels=labels, average="macro", zero_division=0)), "acceptable_hit_rate": float(np.mean(acc_hit)),
           "macro_f1_classes": labels, "majority_baseline": Counter(y).most_common(1)[0][1] / len(y), "class_support": dict(Counter(y)),
           "prompt_sha256": records[0].prompt_sha256 if records else None, "model": records[0].model if records else None}
    if groups:
        g = np.array([groups[i] for i in ids]); ug = np.unique(g); rng = np.random.default_rng(seed); yy, pp = np.array(y), np.array(p)
        by = {u: np.where(g == u)[0] for u in ug}; vals = []
        for _ in range(reps):
            idx = np.concatenate([by[u] for u in rng.choice(ug, len(ug))]); vals.append(f1_score(yy[idx], pp[idx], labels=labels, average="macro", zero_division=0))
        out["macro_f1_ci95_cluster_bootstrap"] = [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]
    return out
