"""Pilot annotation analysis: two independent LLM annotators, agreement, provenance-separated labels.

Provenance rule: labels carry ``label_source`` in {synthetic, llm_consensus, llm_single, human}. LLM agreement is
*never* reported or stored as human consensus. A stratified reserve is held out for future human validation and
excluded from any LLM-label training/evaluation.
"""
from __future__ import annotations

import random
from collections import Counter, defaultdict

from .annotations import Annotation, BASE_CLASSES, cohen_kappa


def align(a: list, b: list) -> list:
    ma, mb = {x.item_id: x for x in a}, {x.item_id: x for x in b}
    if set(ma) != set(mb):
        raise ValueError("annotators must cover the same items")
    for x in list(ma.values()) + list(mb.values()):
        if x.annotator_type != "llm":
            raise ValueError("pilot expects llm annotators")
    if {x.annotator_id for x in a} == {x.annotator_id for x in b}:
        raise ValueError("annotators must be different")
    return [(ma[i], mb[i]) for i in sorted(ma)]


def agreement_report(pairs: list) -> dict:
    xs, ys = [p[0].primary for p in pairs], [p[1].primary for p in pairs]
    n = len(pairs)
    agree = sum(x == y for x, y in zip(xs, ys))
    a_in_b = sum(p[0].primary in p[1].acceptable for p in pairs)
    b_in_a = sum(p[1].primary in p[0].acceptable for p in pairs)
    overlap = sum(bool(set(p[0].acceptable) & set(p[1].acceptable)) for p in pairs)
    jac = sum(len(set(p[0].acceptable) & set(p[1].acceptable)) / len(set(p[0].acceptable) | set(p[1].acceptable)) for p in pairs) / n
    disc = Counter((p[0].primary, p[1].primary) for p in pairs if p[0].primary != p[1].primary)
    return {"n": n, "annotator_a": pairs[0][0].annotator_id, "annotator_b": pairs[0][1].annotator_id,
            "percent_agreement_primary": agree / n, "cohens_kappa_primary": cohen_kappa(xs, ys),
            "a_primary_in_b_acceptable": a_in_b / n, "b_primary_in_a_acceptable": b_in_a / n,
            "acceptable_sets_intersect": overlap / n, "mean_acceptable_jaccard": jac,
            "class_counts_a": dict(Counter(xs)), "class_counts_b": dict(Counter(ys)),
            "discrepancy_pairs": [{"a": k[0], "b": k[1], "count": v} for k, v in disc.most_common()],
            "note": "agreement between two LLMs; NOT human consensus"}


def consensus_labels(pairs: list) -> dict:
    """item_id -> {label, acceptable, label_source, status}. Agreement => llm_consensus; else unresolved (no label)."""
    out = {}
    for a, b in pairs:
        if a.primary == b.primary:
            out[a.item_id] = {"label": a.primary, "acceptable": sorted(set(a.acceptable) | set(b.acceptable)),
                              "label_source": "llm_consensus", "status": "agree"}
        else:
            out[a.item_id] = {"label": None, "acceptable": sorted(set(a.acceptable) & set(b.acceptable)),
                              "label_source": "llm_single", "status": "disagree", "candidates": [a.primary, b.primary]}
    return out


def stratified_reserve(strata: dict, k: int, seed: int) -> list:
    """Pick k ids stratified proportionally (largest remainder), at least one per non-empty stratum when k allows."""
    groups = defaultdict(list)
    for i in sorted(strata):
        groups[strata[i]].append(i)
    n = sum(len(v) for v in groups.values())
    if k > n:
        raise ValueError("k larger than population")
    names = sorted(groups)
    quota = {g: len(groups[g]) * k / n for g in names}
    take = {g: min(len(groups[g]), max(1 if k >= len(names) else 0, int(quota[g]))) for g in names}
    while sum(take.values()) > k:
        g = max((g for g in names if take[g] > 1), key=lambda g: take[g] - quota[g])
        take[g] -= 1
    rem = sorted(names, key=lambda g: (-(quota[g] - take[g]), g))
    while sum(take.values()) < k:
        for g in rem:
            if sum(take.values()) < k and take[g] < len(groups[g]):
                take[g] += 1
    rng = random.Random(seed)
    chosen = []
    for g in names:
        pool = list(groups[g])
        rng.shuffle(pool)
        chosen += pool[:take[g]]
    return sorted(chosen)
