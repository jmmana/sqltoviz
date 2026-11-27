"""Deduplication and leakage-safe grouped splits.

* Exact + near-duplicate removal on normalized SQL (literals and identifiers case/spacing
  collapsed) so paraphrases of one query cannot land in different splits.
* Splits are *grouped*: every item of a group (database / schema family) goes to exactly
  one of train/val/test, so test measures generalisation to unseen schemas.
* Group assignment is greedy and class-balanced: groups are placed so that each split's
  class distribution tracks the global one (stratified group split), deterministically from a seed.
* ``audit_splits`` re-checks all invariants and is run in tests and in the notebook.
"""
from __future__ import annotations

import hashlib
import random
import re
from collections import Counter, defaultdict

_STR = re.compile(r"'(?:[^']|'')*'|\"(?:[^\"]|\"\")*\"")
_NUM = re.compile(r"\b\d+(?:\.\d+)?\b")
_WS = re.compile(r"\s+")


def normalize_sql(sql: str) -> str:
    s = _STR.sub("?", sql)
    s = _NUM.sub("?", s)
    s = _WS.sub(" ", s.strip().rstrip(";")).lower()
    return s


def sql_fingerprint(sql: str) -> str:
    return hashlib.sha256(normalize_sql(sql).encode()).hexdigest()[:16]


def dedup(items: list, key=lambda x: x["sql"], group=lambda x: x["db_id"]) -> tuple:
    """Keep the first (by sorted item_id) of each (group, normalized-SQL) cluster.

    Dedup is *within group* on the template and *across groups* on exact text hash of schema-free
    templates is intentionally NOT merged (same SQL on different schemas are different tasks), but
    exact cross-group duplicates are reported in ``stats['cross_group_dup_templates']``.
    """
    seen = {}
    kept, dropped = [], []
    tmpl_groups = defaultdict(set)
    for it in sorted(items, key=lambda x: x["item_id"]):
        fp = sql_fingerprint(key(it))
        tmpl_groups[fp].add(group(it))
        k = (group(it), fp)
        if k in seen:
            dropped.append({"item_id": it["item_id"], "duplicate_of": seen[k]})
        else:
            seen[k] = it["item_id"]
            kept.append(it)
    stats = {"input": len(items), "kept": len(kept), "dropped": len(dropped),
             "cross_group_dup_templates": sum(1 for g in tmpl_groups.values() if len(g) > 1)}
    return kept, dropped, stats


def grouped_stratified_split(items: list, label=lambda x: x["label"], group=lambda x: x["db_id"],
                             ratios=(0.7, 0.15, 0.15), seed: int = 0) -> dict:
    """Return {item_id: 'train'|'val'|'test'}; whole groups are assigned to one split."""
    if abs(sum(ratios) - 1) > 1e-9 or any(r <= 0 for r in ratios):
        raise ValueError("ratios must be positive and sum to 1")
    names = ("train", "val", "test")
    by_group = defaultdict(list)
    for it in items:
        by_group[group(it)].append(it)
    classes = sorted({label(i) for i in items})
    total = len(items)
    target = {s: r * total for s, r in zip(names, ratios)}
    glob = Counter(label(i) for i in items)
    want = {s: {c: glob[c] * r for c in classes} for s, r in zip(names, ratios)}
    have = {s: Counter() for s in names}
    size = {s: 0 for s in names}
    rng = random.Random(seed)
    order = sorted(by_group, key=lambda g: (-len(by_group[g]), hashlib.md5(f"{seed}:{g}".encode()).hexdigest()))
    # shuffle among equal-size groups deterministically
    rng.shuffle(order)
    order.sort(key=lambda g: -len(by_group[g]))
    assign = {}
    for g in order:
        gc = Counter(label(i) for i in by_group[g])

        def cost(s):
            fill = (size[s] + len(by_group[g])) / max(target[s], 1)      # fill ratio after placement
            imb = sum(abs((have[s][c] + gc[c]) - want[s][c]) / max(want[s][c], 1) for c in classes if gc[c])
            return fill * 4 + imb / max(len(classes), 1)

        best = min(names, key=cost)
        for it in by_group[g]:
            assign[it["item_id"]] = best
        have[best].update(gc)
        size[best] += len(by_group[g])
    return assign


def audit_splits(items: list, assign: dict, label=lambda x: x["label"], group=lambda x: x["db_id"],
                 key=lambda x: x["sql"]) -> dict:
    """Verify leakage invariants; raises AssertionError on violation; returns a report."""
    ids = [i["item_id"] for i in items]
    assert len(ids) == len(set(ids)), "duplicate item ids"
    assert set(ids) == set(assign), "assignment does not cover items exactly"
    g2s = defaultdict(set)
    f2s = defaultdict(set)
    for it in items:
        g2s[group(it)].add(assign[it["item_id"]])
        f2s[(group(it), sql_fingerprint(key(it)))].add(assign[it["item_id"]])
    split_groups = [g for g, s in g2s.items() if len(s) > 1]
    assert not split_groups, f"groups spanning splits: {split_groups[:5]}"
    assert all(len(s) == 1 for s in f2s.values()), "near-duplicate template spans splits"
    rep = {"n": len(items), "splits": {}}
    for s in ("train", "val", "test"):
        sub = [i for i in items if assign[i["item_id"]] == s]
        rep["splits"][s] = {"n": len(sub), "groups": len({group(i) for i in sub}), "classes": dict(Counter(label(i) for i in sub))}
    return rep
