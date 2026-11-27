"""Independent chart annotations: schema, validation, agreement and adjudication.

Independence rules (enforced in code):
* annotator ``type`` is declared (human | llm | rule); rule/heuristic labels are
  never ground truth and are rejected by :func:`validate_for_ground_truth`;
* blind task packs contain only SQL text and a result preview - never model
  scores, SqlVizSpec feature values, rule IDs or the source corpus' own chart label;
* labels are over the 10 base ONNX classes (final 21 outputs are derived
  deterministically by the SDK, not annotated).
"""
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

BASE_CLASSES = ("kpi", "bar", "horizontal_bar", "stacked_bar", "line", "area", "donut", "scatter", "heatmap", "table")
ANNOTATOR_TYPES = ("human", "llm", "rule")
FORBIDDEN_PACK_KEYS = {"label", "chart", "chart_type", "features", "scores", "rule_ids", "prediction", "vis_obj", "vis_query"}


class AnnotationError(ValueError):
    pass


@dataclass(frozen=True)
class Annotation:
    item_id: str
    annotator_id: str
    annotator_type: str
    primary: str
    acceptable: tuple
    confidence: int          # 1..3
    rationale: str = ""

    @staticmethod
    def from_dict(d: dict) -> "Annotation":
        a = Annotation(d["item_id"], d["annotator_id"], d["annotator_type"], d["primary"],
                       tuple(d.get("acceptable") or (d["primary"],)), int(d["confidence"]), d.get("rationale", ""))
        a.validate()
        return a

    def validate(self) -> None:
        if self.annotator_type not in ANNOTATOR_TYPES:
            raise AnnotationError(f"annotator_type {self.annotator_type!r}")
        if self.primary not in BASE_CLASSES:
            raise AnnotationError(f"unknown class {self.primary!r}")
        bad = [c for c in self.acceptable if c not in BASE_CLASSES]
        if bad:
            raise AnnotationError(f"unknown acceptable classes {bad}")
        if self.primary not in self.acceptable:
            raise AnnotationError("primary must be in acceptable")
        if self.confidence not in (1, 2, 3):
            raise AnnotationError("confidence must be 1..3")
        if not self.item_id or not self.annotator_id:
            raise AnnotationError("item_id and annotator_id required")


def validate_for_ground_truth(anns: list) -> None:
    if any(a.annotator_type == "rule" for a in anns):
        raise AnnotationError("rule-based labels cannot be ground truth")
    seen = set()
    for a in anns:
        k = (a.item_id, a.annotator_id)
        if k in seen:
            raise AnnotationError(f"duplicate annotation {k}")
        seen.add(k)


def assert_blind(item: dict) -> None:
    leaked = FORBIDDEN_PACK_KEYS & set(item)
    if leaked:
        raise AnnotationError(f"task item leaks {sorted(leaked)}")


def build_task_pack(candidates: list, n: int, seed: int, group_key: str = "db_id") -> list:
    """Deterministic sample spread across groups (round-robin over shuffled groups)."""
    rng = random.Random(seed)
    by_group: dict = defaultdict(list)
    for c in sorted(candidates, key=lambda c: c["item_id"]):
        assert_blind(c)
        by_group[c[group_key]].append(c)
    groups = sorted(by_group)
    rng.shuffle(groups)
    for g in groups:
        rng.shuffle(by_group[g])
    out: list = []
    while len(out) < n and any(by_group.values()):
        for g in groups:
            if by_group[g] and len(out) < n:
                out.append(by_group[g].pop())
    return out


def _matrix(anns: list, field: str = "primary"):
    items: dict = defaultdict(dict)
    for a in anns:
        items[a.item_id][a.annotator_id] = getattr(a, field)
    return items


def cohen_kappa(x: list, y: list) -> float:
    if len(x) != len(y) or not x:
        raise AnnotationError("need equal-length non-empty label lists")
    n = len(x)
    po = sum(a == b for a, b in zip(x, y)) / n
    cx, cy = Counter(x), Counter(y)
    pe = sum(cx[k] * cy[k] for k in set(cx) | set(cy)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def pairwise_kappa(anns: list) -> dict:
    m = _matrix(anns)
    annotators = sorted({a.annotator_id for a in anns})
    out = {}
    for p, q in combinations(annotators, 2):
        shared = [i for i, v in m.items() if p in v and q in v]
        if shared:
            out[(p, q)] = {"n": len(shared), "kappa": cohen_kappa([m[i][p] for i in shared], [m[i][q] for i in shared])}
    return out


def krippendorff_alpha_nominal(anns: list) -> float:
    """Krippendorff's alpha for nominal data with missing values."""
    m = {i: list(v.values()) for i, v in _matrix(anns).items() if len(v) >= 2}
    if not m:
        raise AnnotationError("no item with >=2 annotations")
    coincid: Counter = Counter()
    for vals in m.values():
        k = len(vals)
        for a, b in combinations(range(k), 2):
            coincid[(vals[a], vals[b])] += 1 / (k - 1)
            coincid[(vals[b], vals[a])] += 1 / (k - 1)
    n_c: Counter = Counter()
    for (a, _b), w in coincid.items():
        n_c[a] += w
    n = sum(n_c.values())
    do = sum(w for (a, b), w in coincid.items() if a != b)
    de = sum(n_c[a] * n_c[b] for a in n_c for b in n_c if a != b) / (n - 1) if n > 1 else 0
    return 1.0 if de == 0 else 1 - do / de


def adjudicate(anns: list, min_annotators: int = 2) -> dict:
    """Majority vote on ``primary``; ties or low support are flagged for manual adjudication."""
    res = {}
    for item, votes in _matrix(anns).items():
        c = Counter(votes.values())
        top = c.most_common()
        if len(votes) < min_annotators:
            res[item] = {"label": None, "status": "insufficient_annotators", "votes": dict(c)}
        elif len(top) > 1 and top[0][1] == top[1][1]:
            res[item] = {"label": None, "status": "tie_needs_adjudication", "votes": dict(c)}
        else:
            res[item] = {"label": top[0][0], "status": "unanimous" if len(top) == 1 else "majority", "votes": dict(c)}
    return res


def load_jsonl(path) -> list:
    return [Annotation.from_dict(json.loads(l)) for l in Path(path).read_text().splitlines() if l.strip()]
