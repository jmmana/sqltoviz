"""Role supervision from expert-authored Vega-Lite example specs (vega/vega-lite, BSD-3-Clause).

Each column used by an encoding channel gets a role from the contract's five roles
(x_axis, y_axis, color_series, size_or_secondary, ignore_tooltip); unused columns become ignore_tooltip.
Only specs that are safe to read as (table, roles) are used: inline data, no data transforms/joins, every encoded
field exists as a column. Priority when a column serves several channels: x > y > color > size/secondary > tooltip.
Roles here come from visualization authors, independent of our rules and of LLMs; they are NOT SQL-aware
(the SQL context is fixed to `SELECT * FROM data`), which is a stated limitation.
"""
from __future__ import annotations

ROLES = ("x_axis", "y_axis", "color_series", "size_or_secondary", "ignore_tooltip")
CHANNEL_ROLE = {"x": 0, "y": 1, "color": 2, "fill": 2, "stroke": 2, "detail": 2, "column": 2, "row": 2, "xOffset": 2, "yOffset": 3,
                "size": 3, "shape": 3, "opacity": 3, "x2": 3, "y2": 3, "theta": 1, "radius": 3, "tooltip": 4, "text": 4, "href": 4, "order": 4}


def _fields(enc: dict):
    for ch, v in enc.items():
        if ch not in CHANNEL_ROLE:
            continue
        for item in (v if isinstance(v, list) else [v]):
            if isinstance(item, dict) and isinstance(item.get("field"), str) and "." not in item["field"] and "\\" not in item["field"]:
                yield ch, item["field"]


def spec_to_example(spec: dict, max_rows: int = 500):
    """Return {columns, rows, roles} or (None, reason)."""
    data = spec.get("data") or {}
    vals = data.get("values")
    if not isinstance(vals, list) or not vals or not all(isinstance(r, dict) for r in vals):
        return None, "no inline row data"
    if spec.get("transform") or any(isinstance(l, dict) and l.get("transform") for l in spec.get("layer", [])):
        return None, "has transform"
    if any(k in spec for k in ("hconcat", "vconcat", "concat", "facet", "repeat")):
        return None, "composite"
    encs = [spec.get("encoding") or {}] + [l.get("encoding") or {} for l in spec.get("layer", []) if isinstance(l, dict)]
    cols = []
    for r in vals:
        for k in r:
            if k not in cols:
                cols.append(k)
    best = {}
    for e in encs:
        for ch, f in _fields(e):
            if f not in cols:
                return None, "encoded field not a data column"
            best[f] = min(best.get(f, 9), CHANNEL_ROLE[ch])
    if not best:
        return None, "no field encodings"
    if len(cols) > 128 or len(vals) > 100000:
        return None, "outside contract"
    rows = [[r.get(c) for c in cols] for r in vals[:max_rows]]
    return {"columns": cols, "rows": rows, "roles": [ROLES[best.get(c, 4)] for c in cols]}, "ok"


def fetch_examples(sha: str, cache_path=None) -> tuple:
    """Download all examples/specs/*.vl.json at a pinned vega-lite commit; return (examples, stats, source_listing)."""
    import json
    import urllib.request
    from collections import Counter
    api = f"https://api.github.com/repos/vega/vega-lite/git/trees/{sha}?recursive=1"
    tree = json.loads(urllib.request.urlopen(urllib.request.Request(api, headers={"User-Agent": "sqltoviz-data"}), timeout=60).read())["tree"]
    paths = sorted(t["path"] for t in tree if t["path"].startswith("examples/specs/") and t["path"].endswith(".vl.json"))
    stats, out = Counter(), []
    for p in paths:
        spec = json.loads(urllib.request.urlopen(f"https://raw.githubusercontent.com/vega/vega-lite/{sha}/{p}", timeout=60).read())
        ex, why = spec_to_example(spec)
        stats[why] += 1
        if ex:
            out.append({"spec": p.rsplit("/", 1)[1], **ex})
    if cache_path:
        json.dump(out, open(cache_path, "w"))
    return out, dict(stats), len(paths)
