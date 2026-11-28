"""External, human-authored evaluation of SqlToViz chart recommendation on nvBench (Luo et al., SIGMOD 2021).

Usage: eval_nvbench.py [--root DIR] [--out reports/nvbench_eval.json] [--reps 2000] [--limit N]

nvBench data and the Spider databases it ships are downloaded LOCALLY to ``<root>/mit-readme-declared/nvbench`` (default root: research/kaggle/data,
git-ignored). NEVER commit or redistribute them (license ambiguous: README says MIT, no LICENSE file; Spider DBs are CC BY-SA 4.0). The report holds only
aggregate metrics, hashes and provenance: no item text, SQL, rows or ids.

Provenance: external_human_authored_nvbench, confirmatory=false. nvBench labels are the chart requested in natural language, NOT the "best" chart,
and cover only 5 of the 10 base classes. See research/paper/NVBENCH_EVALUATION.md.
"""
from __future__ import annotations

import argparse, hashlib, json, os, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
KAGGLE = HERE.parent
REPO = KAGGLE.parents[1]
sys.path.insert(0, str(KAGGLE))
sys.path.insert(0, str(REPO / "packages" / "python"))

import numpy as np  # noqa: E402

PROVENANCE = "external_human_authored_nvbench"
BASE_URL = "https://raw.githubusercontent.com/TsinghuaDatabaseGroup/nvBench/main"
NVBENCH_SHA256 = "8c85a9454fe1343074ba915bcbb379f170ab62bb1279b6a7aed23255e6eefbcf"
DATABASES_SHA256 = "a2e22bf648f6d8e4c387d85f75962931976f1756338b41d025de528c8ff2da3d"  # trust-on-first-use (no upstream hash published)
DATABASES_SIZE = 98291742
NAMESPACE = "mit-readme-declared/nvbench"
FORBIDDEN_TRACKED_NAMES = ("NVBench.json", "databases.zip")

# Explicit, documented mapping: nvBench "chart" field -> our base class. Anything not listed is dropped (and counted), never guessed.
VIS_MAP = {"Bar": "bar", "Stacked Bar": "stacked_bar", "Pie": "donut", "Line": "line", "Grouping Line": "line",
           "Scatter": "scatter", "Grouping Scatter": "scatter"}
COVERED = ("bar", "stacked_bar", "line", "donut", "scatter")   # the 5 of 10 base classes with a human source
MIN_SUPPORT = 5


def map_vis_type(v: str) -> str | None:
    return VIS_MAP.get(v)


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tracked_nvbench_files(repo: Path = REPO) -> list:
    """Paths tracked by git that look like nvBench data (guard against redistribution)."""
    import subprocess
    out = subprocess.run(["git", "-C", str(repo), "ls-files"], capture_output=True, text=True, check=True).stdout.splitlines()
    bad = []
    for p in out:
        low = p.lower()
        if os.path.basename(p) in FORBIDDEN_TRACKED_NAMES or "mit-readme-declared" in low or "/nvbench/" in low.replace("\\", "/") and low.endswith((".json", ".jsonl", ".sqlite", ".zip", ".csv")):
            bad.append(p)
    return bad


def acquire(root: Path) -> tuple:
    from sqltoviz_data import acquire as A
    d = root / NAMESPACE
    d.mkdir(parents=True, exist_ok=True)
    nv, zp = d / "NVBench.json", d / "databases.zip"
    if not nv.exists():
        A.download(f"{BASE_URL}/NVBench.json", nv)
    if sha256_file(nv) != NVBENCH_SHA256:
        nv.unlink()
        raise SystemExit("NVBench.json SHA256 mismatch: file deleted, run rejected")
    dbdir = d / "databases"
    if not dbdir.exists():
        if not zp.exists():
            A.download(f"{BASE_URL}/databases.zip", zp)
        if zp.stat().st_size != DATABASES_SIZE or sha256_file(zp) != DATABASES_SHA256:
            zp.unlink()
            raise SystemExit("databases.zip size/SHA256 mismatch: file deleted, run rejected")
        A.safe_extract(zp, dbdir)
    return nv, dbdir / "database"


def chart_data_rows(vo: dict) -> tuple:
    """Rebuild the chart's own data (after nvBench binning/grouping) as a long table: x, y[, series]."""
    xs, ys, cl = vo["x_data"], vo["y_data"], vo.get("classify") or []
    cols = [vo["x_name"], vo["y_name"]] + (["series"] if cl else [])
    rows = []
    for i, y in enumerate(ys):
        x = xs[i] if i < len(xs) else xs[0]
        for j in range(min(len(x), len(y))):
            rows.append([x[j], y[j]] + ([cl[i] if i < len(cl) else None] if cl else []))
    return cols, rows


def bootstrap(y, preds: dict, groups, labels, reps: int, seed: int) -> dict:
    """Cluster (database) bootstrap, same resamples for all systems; per-database confusion matrices make it fast. 95% percentile CIs."""
    y, groups = np.array(y), np.array(groups)
    ug = np.unique(groups)
    k = len(labels)
    ix = {c: i for i, c in enumerate(labels)}
    gi = {g: i for i, g in enumerate(ug)}
    tot = np.zeros(len(ug))
    true_cnt = np.zeros((len(ug), k))
    for t, g in zip(y, groups):
        tot[gi[g]] += 1
        if t in ix:
            true_cnt[gi[g], ix[t]] += 1
    correct = {n: np.zeros(len(ug)) for n in preds}
    pred_cnt = {n: np.zeros((len(ug), k)) for n in preds}
    tp = {n: np.zeros((len(ug), k)) for n in preds}
    for n, p in preds.items():
        for t, q, g in zip(y, p, groups):
            if t == q:
                correct[n][gi[g]] += 1
                if t in ix:
                    tp[n][gi[g], ix[t]] += 1
            if q in ix:
                pred_cnt[n][gi[g], ix[q]] += 1
    rng = np.random.default_rng(seed)
    accs = {n: [] for n in preds}
    f1s = {n: [] for n in preds}
    for _ in range(reps):
        s = rng.integers(0, len(ug), len(ug))
        N = tot[s].sum()
        for n in preds:
            accs[n].append(correct[n][s].sum() / N)
            TP, P, T = tp[n][s].sum(0), pred_cnt[n][s].sum(0), true_cnt[s].sum(0)
            den = P + T
            f1 = np.where(den > 0, 2 * TP / np.where(den > 0, den, 1), 0.0)
            f1s[n].append(f1.mean())
    ci = lambda v: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]
    out = {"reps": reps, "seed": seed, "n_clusters": int(len(ug)), "cluster": "db_id",
           "accuracy_ci95": {n: ci(accs[n]) for n in preds}, "macro_f1_ci95": {n: ci(f1s[n]) for n in preds}, "pairwise": {}}
    names = list(preds)
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            for nm, src in (("accuracy", accs), ("macro_f1", f1s)):
                d = np.array(src[names[a]]) - np.array(src[names[b]])
                lo, hi = ci(d)
                out["pairwise"][f"{nm}: {names[a]} - {names[b]}"] = {"mean_diff": float(d.mean()), "ci95": [lo, hi], "excludes_zero": bool(lo > 0 or hi < 0)}
    return out


def evaluate(y, preds: dict, groups, top2: dict, reps: int, seed: int = 0) -> dict:
    from sklearn.metrics import f1_score, precision_recall_fscore_support
    support = Counter(y)
    labels = [c for c in COVERED if support[c] >= MIN_SUPPORT]
    res = {"n": len(y), "support": {c: support.get(c, 0) for c in COVERED}, "macro_f1_classes": labels, "systems": {}}
    for n, p in preds.items():
        pr, rc, f1, _ = precision_recall_fscore_support(y, p, labels=labels, zero_division=0)
        res["systems"][n] = {
            "accuracy": float(np.mean([a == b for a, b in zip(y, p)])),
            "macro_f1_covered": float(f1_score(y, p, labels=labels, average="macro", zero_division=0)),
            "per_class": {c: {"precision": float(pr[i]), "recall": float(rc[i]), "f1": float(f1[i])} for i, c in enumerate(labels)},
            "predicted_distribution": dict(Counter(p)),
            "top2_accuracy": (float(np.mean([t in s for t, s in zip(y, top2[n])])) if n in top2 else None)}
    res["bootstrap"] = bootstrap(y, preds, groups, labels, reps, seed)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(KAGGLE / "data"))
    ap.add_argument("--out", default=str(KAGGLE / "reports" / "nvbench_eval.json"))
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--limit", type=int)
    a = ap.parse_args(argv)
    tracked = tracked_nvbench_files()
    if tracked:
        raise SystemExit(f"refusing to run: nvBench-looking files are tracked by git: {tracked}")
    from sqltoviz_data import sandbox as SB, features as F
    from sqltoviz import Engine
    from sqltoviz._contract import BASE_CLASSES
    nv, dbroot = acquire(Path(a.root))
    data = json.load(open(nv))
    eng = Engine.default()
    man = eng.manifest
    items = list(data.items())[: a.limit] if a.limit else list(data.items())
    raw_support = Counter(v["chart"] for _, v in items)
    views = {"sql_result": [], "chart_data": []}
    drops = Counter()
    cache = {}
    for iid, v in items:
        y = map_vis_type(v["chart"])
        if y is None:
            drops["unmapped_vis_type"] += 1
            continue
        sql, db = v["vis_query"]["data_part"]["sql_part"], v["db_id"]
        binned = bool(v["vis_query"]["data_part"]["binning"])
        for view in views:
            if view == "sql_result":
                key = (db, sql)
                if key not in cache:
                    cache[key] = SB.execute(dbroot / db / f"{db}.sqlite", sql)
                r = cache[key]
                if r.status != SB.OK:
                    drops[f"sql_result:{r.status}"] += 1
                    continue
                if r.truncated:
                    drops["sql_result:truncated"] += 1
                    continue
                cols, rows = r.columns, r.rows
            else:
                cols, rows = chart_data_rows(v["vis_obj"])
            if not rows:
                drops[f"{view}:empty"] += 1
                continue
            try:
                out = eng.recommend(sql, [{"name": str(c)} for c in cols] if len(set(map(str, cols))) == len(cols) else
                                    [{"name": f"{c}_{i}"} for i, c in enumerate(cols)], rows)
            except (F.FeatureError, ValueError, TypeError, KeyError) as e:
                drops[f"{view}:engine_{type(e).__name__}"] += 1
                continue
            sc = out["scores"]
            order = sorted(BASE_CLASSES, key=lambda c: (-sc[c], BASE_CLASSES.index(c)))
            views[view].append({"y": y, "db": db, "binned": binned, "model": out["final_class"], "model_raw": out["base_class"],
                                "rules": out["rule_class"], "top2": order[:2], "top2_final": [out["final_class"]] + [c for c in order if c != out["final_class"]][:1]})
    reports = {}
    for view, recs in views.items():
        sub = {"all": recs, "no_binning": [r for r in recs if not r["binned"]]}
        reports[view] = {}
        for sname, rs in sub.items():
            if not rs:
                continue
            y = [r["y"] for r in rs]
            preds = {"model_constrained": [r["model"] for r in rs], "model_argmax": [r["model_raw"] for r in rs],
                     "rules_baseline": [r["rules"] for r in rs], "always_bar": ["bar"] * len(rs)}
            top2 = {"model_argmax": [r["top2"] for r in rs], "model_constrained": [r["top2_final"] for r in rs]}
            reports[view][sname] = evaluate(y, preds, [r["db"] for r in rs], top2, a.reps)
    report = {"provenance": PROVENANCE, "confirmatory": False,
              "banner": "external human-authored benchmark (nvBench); label = chart requested in natural language, not the best chart; covers 5 of 10 base classes; models remain EXPERIMENTAL candidates, not validated",
              "contract_version": F.CONTRACT_VERSION, "contract_sha256": F.CONTRACT_SHA256,
              "models": {k: {"sha256": man[k]["sha256"], "status": man[k]["status"], "version": man[k]["version"]} for k in ("chart", "role")},
              "nvbench": {"file": "NVBench.json", "sha256": NVBENCH_SHA256, "databases_zip_sha256_tofu": DATABASES_SHA256, "license_note": "README says MIT, no LICENSE file; Spider DBs CC BY-SA 4.0; data not redistributed"},
              "vis_type_mapping": VIS_MAP, "covered_classes": list(COVERED), "uncovered_classes": [c for c in BASE_CLASSES if c not in COVERED],
              "n_items_in_file": len(items), "nvbench_vis_type_counts": dict(raw_support), "dropped": dict(drops),
              "views": {"sql_result": "SQL text executed verbatim in the read-only sandbox on the Spider DB; binned items lack nvBench's binning step",
                        "chart_data": "nvBench's own vis_obj data (post-binning/grouping) as a long table; SQL text passed is the data_part SQL"},
              "top2_definition": "model: top-2 by raw chart_scores; rules baseline and always_bar expose no alternatives (null)",
              "results": reports}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(a.out, "w"), indent=1, sort_keys=True)
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
