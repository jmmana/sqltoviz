"""Generate the three Kaggle notebooks (thin: all logic lives in the tested `sqltoviz_data` package)."""
import nbformat as nbf
from pathlib import Path

BOOT = '''import os, sys, json, subprocess, pathlib, time
MODE = os.environ.get("SQLTOVIZ_MODE", "smoke")            # "smoke" (minutes, subset) | "full"
SEED = 20261127
COMMIT = os.environ.get("SQLTOVIZ_COMMIT", "development")   # pin a commit SHA for publishable runs
REPO = os.environ.get("SQLTOVIZ_REPO")
if not REPO:                                                # Kaggle: clone the repository at the pinned commit
    REPO = "/kaggle/working/sqltoviz"
    if not os.path.exists(REPO):
        subprocess.run(["git", "clone", "https://github.com/jmmana/sqltoviz", REPO], check=True)
        subprocess.run(["git", "-C", REPO, "checkout", COMMIT], check=True)
sys.path.insert(0, f"{REPO}/research/kaggle")
OUT = os.environ.get("SQLTOVIZ_OUT", "/kaggle/working/out"); os.makedirs(OUT, exist_ok=True)
DATA = os.environ.get("SQLTOVIZ_DATA", "/kaggle/working/data")
GIT = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
print("mode", MODE, "| repo commit", GIT, "| out", OUT)
from sqltoviz_data import features as F
F.load_contract()                                           # raises if the contract bytes differ from the pinned SHA256
print(F.CONTRACT_VERSION, F.CONTRACT_SHA256)'''

NB1 = [
("md", """# 01 - Build the hybrid dataset (E01-09, #27)
Provenance, license-separated namespaces, deterministic dedup + grouped splits, label-leak audit, contract-pinned features.
**Parameters** (env): `SQLTOVIZ_MODE` smoke|full, `SQLTOVIZ_COMMIT`, `SQLTOVIZ_DATA`, `SQLTOVIZ_OUT`. Code is Apache-2.0; Spider/BIRD material stays in `cc-by-sa-4.0/` (CC BY-SA 4.0); synthetic data in `apache-2.0/`.
Labels: synthetic (by construction) and LLM pilot labels are kept separate; there are **no human labels yet** (100 ids reserved)."""),
("code", BOOT),
("md", "## 1. Acquire Spider / BIRD (checksum-verified; skipped if already present)"),
("code", '''import pathlib
from sqltoviz_data import acquire, pipeline as P, splits as S, synthgen as G, leakage as L, experiment as E
NS = f"{DATA}/cc-by-sa-4.0"
acq = []
if not (os.path.exists(f"{NS}/spider/spider_data/dev.json") and os.path.exists(f"{NS}/bird_dev")):
    man = acquire.load_manifest(pathlib.Path(REPO) / "research/kaggle/manifests/sources.json")
    acq = [acquire.acquire(n, man[n], pathlib.Path(DATA)) for n in ("spider", "bird_dev")]
print(json.dumps(acq, indent=1) if acq else "sources already present at " + NS)'''),
("md", "## 2. Real candidates: execute gold SQL in the read-only sandbox, keep within-contract results"),
("code", '''MAXS = 700 if MODE == "smoke" else None
real, real_stats = P.real_candidates(NS, max_per_source=MAXS)
print(json.dumps(real_stats, indent=1)); print(len(real), "executable items")'''),
("md", "## 3. Deduplicate (within database) and split by database (no schema in two splits)"),
("code", '''kept, dropped, dstats = S.dedup(real, group=lambda x: x["db_id"])
for it in kept: it["label"] = "unlabelled"             # real items have no chart label here; labels come from annotation
assign = S.grouped_stratified_split(kept, label=lambda x: x["label"], group=lambda x: x["db_id"], seed=SEED)
audit = S.audit_splits(kept, assign, label=lambda x: x["label"], group=lambda x: x["db_id"])   # raises on leakage
print(dstats); print({k: (v["n"], v["groups"]) for k, v in audit["splits"].items()})'''),
("md", "## 4. Synthetic data (class-agnostic schemas/templates) + measured label-leakage audit"),
("code", '''NPC = 150 if MODE == "smoke" else 2000
syn = G.generate(NPC, SEED)
G.assert_no_chart_vocabulary(syn)
leak = L.report(syn, seed=0)
print("structural ceiling", leak["structural_ceiling_accuracy"])
for k, v in leak["views"].items(): print(f"{k:26s} acc={v['accuracy']:.3f} macroF1={v['macro_f1']:.3f}")
assert leak["views"]["sql_features16"]["accuracy"] <= leak["structural_ceiling_accuracy"] + 0.05, "SQL-only leakage above structural ceiling"
assert leak["views"]["names_only"]["accuracy"] <= leak["structural_ceiling_accuracy"] + 0.05'''),
("md", "## 5. Contract-pinned features and artifacts (license namespaces kept apart)"),
("code", '''for d in ("apache-2.0", "cc-by-sa-4.0", "llm-labels", "reports"): os.makedirs(f"{OUT}/{d}", exist_ok=True)
with open(f"{OUT}/apache-2.0/synthetic.jsonl", "w") as f:
    for it in syn: f.write(json.dumps(it, sort_keys=True) + "\\n")
fs = P.save_features(f"{OUT}/apache-2.0/features_synthetic.npz", syn)
with open(f"{OUT}/cc-by-sa-4.0/real_items.jsonl", "w") as f:
    for it in kept: f.write(json.dumps(it, default=str) + "\\n")
fr = P.save_features(f"{OUT}/cc-by-sa-4.0/features_real.npz", kept)
json.dump(assign, open(f"{OUT}/cc-by-sa-4.0/real_splits.json", "w"))
import shutil
lab = pathlib.Path(REPO) / "research/kaggle/annotations"
for n in ("pilot_llm_labels.jsonl", "human_validation_reserve_ids.json"):
    if (lab / n).exists(): shutil.copy(lab / n, f"{OUT}/llm-labels/{n}")
print(fs, fr)'''),
("code", '''report = {"mode": MODE, "seed": SEED, "repo_commit": GIT, "contract_version": F.CONTRACT_VERSION, "contract_sha256": F.CONTRACT_SHA256,
          "acquisition": acq, "real_candidates": real_stats, "dedup": dstats, "real_split_audit": audit, "synthetic_leakage_audit": leak,
          "synthetic_sha256": E.sha256_items(syn), "feature_files": {"synthetic": fs, "real": fr},
          "label_provenance": {"synthetic": "by construction", "llm": "pilot only (llm-labels/)", "human": "none yet"}}
json.dump(report, open(f"{OUT}/reports/dataset_audit.json", "w"), indent=1, default=str)
files = {"apache-2.0/synthetic.jsonl": "apache-2.0", "apache-2.0/features_synthetic.npz": "apache-2.0",
         "cc-by-sa-4.0/real_items.jsonl": "cc-by-sa-4.0", "cc-by-sa-4.0/features_real.npz": "cc-by-sa-4.0", "cc-by-sa-4.0/real_splits.json": "cc-by-sa-4.0",
         "reports/dataset_audit.json": "apache-2.0"}
for n in ("pilot_llm_labels.jsonl", "human_validation_reserve_ids.json"):
    if os.path.exists(f"{OUT}/llm-labels/{n}"): files[f"llm-labels/{n}"] = "cc-by-sa-4.0"
man = P.write_manifest(OUT, files, {"mode": MODE, "seed": SEED, "repo_commit": GIT})
print(json.dumps({k: v["sha256"][:12] for k, v in man["files"].items()}, indent=1))'''),
]

NB2 = [
("md", """# 02 - Training, baselines and ablation (E01-10, #28)
Five systems under one protocol (rules, SQL-only, data-only, hybrid, hybrid + semantic constraints), leave-one-group-out ablation,
synthetic->real transfer on the LLM-labelled pilot. **Every number states what it measures.** No definitive model is trained here:
the contract readings are under review (FEATURE_INTERPRETATIONS.md); rerun after confirmation. Requires outputs of notebook 01 in `SQLTOVIZ_OUT`."""),
("code", BOOT),
("code", '''import numpy as np, pathlib
from sqltoviz_data import pipeline as P, splits as S, experiment as E, rules as R
for d in ("reports",): os.makedirs(f"{OUT}/{d}", exist_ok=True)
syn = [json.loads(l) for l in open(f"{OUT}/apache-2.0/synthetic.jsonl")]
fs = P.load_features(f"{OUT}/apache-2.0/features_synthetic.npz")          # raises if built with another contract
byid = {it["item_id"]: it for it in syn}
syn = [byid[i] for i in fs["item_ids"]]
X, C = fs["table"], fs["columns"]
print(len(syn), "synthetic items |", F.CONTRACT_VERSION, F.CONTRACT_SHA256[:12])'''),
("md", "## E1 - synthetic -> held-out synthetic schemas (agreement with the generator convention; NOT real accuracy)"),
("code", '''SEEDS = [0] if MODE == "smoke" else [0, 1, 2]
idx = {it["item_id"]: k for k, it in enumerate(syn)}
runs = []
for sd in SEEDS:
    assign = S.grouped_stratified_split(syn, group=lambda x: x["db_id"], seed=sd)
    S.audit_splits(syn, assign, group=lambda x: x["db_id"])
    tr = [i for i in syn if assign[i["item_id"]] == "train"]; te = [i for i in syn if assign[i["item_id"]] == "test"]
    tri, tei = [idx[i["item_id"]] for i in tr], [idx[i["item_id"]] for i in te]
    r = E.evaluate_all(tr, te, seed=sd, Xtr=X[tri], Xte=X[tei], cols_te=[C[k] for k in tei]); r["split_seed"] = sd; runs.append(r)
for s in E.SYSTEMS:
    print(f"{s:16s} macroF1={np.mean([r['systems'][s]['macro_f1'] for r in runs]):.3f} acc={np.mean([r['systems'][s]['accuracy'] for r in runs]):.3f} "
          f"violations={np.mean([r['systems'][s]['semantic_violation_rate'] for r in runs]):.3f}")
e1 = {"experiment": "E1", "measures": "agreement with synthetic generator convention on unseen schemas", "meta": E.run_meta({"mode": MODE, "split_seeds": SEEDS, "n_items": len(syn)}), "runs": runs}
json.dump(e1, open(f"{OUT}/reports/e1.json", "w"), indent=1)'''),
("md", "## Ablation - leave one feature group out (hybrid, same split)"),
("code", '''asg = S.grouped_stratified_split(syn, group=lambda x: x["db_id"], seed=SEEDS[0])
tri = [idx[i["item_id"]] for i in syn if asg[i["item_id"]] == "train"]; tei = [idx[i["item_id"]] for i in syn if asg[i["item_id"]] == "test"]
ab = E.ablate(X[tri], [syn[k]["label"] for k in tri], X[tei], [syn[k]["label"] for k in tei], seed=0)
print("full", round(ab["full"], 3))
for g, v in ab["groups"].items(): print(f"{g:18s} n={v['n_features']:2d} macroF1_without={v['macro_f1_without']:.3f} delta={v['delta_vs_full']:+.3f}")
json.dump({"experiment": "ablation_leave_one_group_out", "meta": E.run_meta({"mode": MODE}), **ab}, open(f"{OUT}/reports/ablation.json", "w"), indent=1)'''),
("md", "## E2 - synthetic-trained -> real Spider queries judged by LLM annotators (transfer; NOT human accuracy)"),
("code", '''labp = f"{OUT}/llm-labels/pilot_llm_labels.jsonl"
if os.path.exists(labp) and os.path.exists(f"{OUT}/cc-by-sa-4.0/features_real.npz"):
    fr = P.load_features(f"{OUT}/cc-by-sa-4.0/features_real.npz")
    real = {json.loads(l)["item_id"]: json.loads(l) for l in open(f"{OUT}/cc-by-sa-4.0/real_items.jsonl")}
    pos = {i: k for k, i in enumerate(fr["item_ids"])}
    labs = [json.loads(l) for l in open(labp)]
    ev = [l for l in labs if l["status"] == "agree" and not l["reserved_for_human_validation"] and l["item_id"] in pos]
    print(len(ev), "LLM-consensus items available (reserved human-validation items excluded)")
    if len(ev) >= 20:
        test = [dict(real[l["item_id"]], label=l["label"], acceptable=set(l["acceptable"])) for l in ev]
        k = [pos[l["item_id"]] for l in ev]
        r2 = E.evaluate_all(syn, test, seed=0, Xtr=X, Xte=fr["table"][k], cols_te=[fr["columns"][i] for i in k])
        print("test majority", r2["test_majority"])
        for s in E.SYSTEMS: print(f"{s:16s} acc={r2['systems'][s]['accuracy']:.3f} violations={r2['systems'][s]['semantic_violation_rate']:.3f}")
        json.dump({"experiment": "E2", "measures": "agreement with LLM consensus on real queries; not human", "meta": E.run_meta({"mode": MODE, "n": len(ev)}), **r2}, open(f"{OUT}/reports/e2.json", "w"), indent=1)
    else: print("pilot items not in this run's subset; skipping E2 (use MODE=full)")
else: print("no pilot labels / real features: E2 skipped")'''),
]

NB3 = [
("md", """# 03 - Export ONNX and golden parity fixtures (E01-11, #29)
Exports the **candidate** chart model (`table_features[batch,32] -> chart_scores[batch,10]`, class order = contract), verifies it against scikit-learn
within atol=rtol=1e-6, and builds >=250 golden fixtures (10 classes, edge cases, rejections) for the Python/TypeScript/.NET SDKs.
The role model is **not** exported: there is no role supervision yet. The artifact is a candidate trained on synthetic data under unconfirmed contract readings - not a final model."""),
("code", BOOT),
("code", '''import numpy as np, pathlib
from sqltoviz_data import pipeline as P, splits as S, onnx_export as OX, golden as GD
for d in ("model", "parity", "reports"): os.makedirs(f"{OUT}/{d}", exist_ok=True)
syn = [json.loads(l) for l in open(f"{OUT}/apache-2.0/synthetic.jsonl")]
fs = P.load_features(f"{OUT}/apache-2.0/features_synthetic.npz")
byid = {it["item_id"]: it for it in syn}; syn = [byid[i] for i in fs["item_ids"]]; X = fs["table"]
asg = S.grouped_stratified_split(syn, group=lambda x: x["db_id"], seed=0)
tri = [k for k, i in enumerate(syn) if asg[i["item_id"]] == "train"]; tei = [k for k, i in enumerate(syn) if asg[i["item_id"]] == "test"]
model = OX.fit_contract_model(X[tri], [syn[k]["label"] for k in tri], seed=0, n_estimators=100 if MODE == "full" else 30)
path = OX.export_chart_model(model, f"{OUT}/model/chart_model_candidate.onnx")
sess = OX.session(path)
ver = OX.verify_against_sklearn(model, sess, X[tei])
print(ver); assert ver["within_tolerance"] and ver["argmax_equal_rate"] == 1.0
print("onnx bytes", pathlib.Path(path).stat().st_size, "sha256", OX.sha256_file(path))'''),
("md", "## Golden parity fixtures (synthetic + hand-crafted only, redistributable under Apache-2.0)"),
("code", '''cases = GD.handcrafted_cases() + GD.synthetic_cases(syn, per_class=25, max_rows=80, seed=1)
g = GD.build_golden(cases, sess)
rep = GD.verify_golden(json.loads(json.dumps(g)), sess)
print({k: rep[k] for k in ("n_cases", "accepted_ok", "rejected_ok", "max_abs_diff")}, "failures:", rep["failures"])
assert rep["failures"] == [] and g["n_cases"] >= 250, g["n_cases"]
from collections import Counter
print(Counter(c.get("generator_label", c["kind"]) for c in g["cases"]))
json.dump(g, open(f"{OUT}/parity/golden_v1.json", "w"))'''),
("md", "## Model card (what the artifact is and is not)"),
("code", '''card = {"status": "CANDIDATE - not final", "contract_version": F.CONTRACT_VERSION, "contract_sha256": F.CONTRACT_SHA256, "repo_commit": GIT,
        "onnx_sha256": OX.sha256_file(path), "class_order": list(OX.CLASSES), "trained_on": "synthetic only (label by construction)",
        "classifier": "RandomForest (fixed defaults, no tuning)", "onnx_vs_sklearn": ver, "golden_cases": g["n_cases"], "golden_verification": {k: rep[k] for k in ("accepted_ok", "rejected_ok", "max_abs_diff")},
        "limitations": ["synthetic labels encode generator conventions", "table-level features cannot separate bar/horizontal_bar and line/area",
                        "contract readings pending review", "role model not trained (no role labels)", "cross-SDK parity not yet measured"]}
json.dump(card, open(f"{OUT}/model/MODEL_CARD.json", "w"), indent=1)
files = {"model/chart_model_candidate.onnx": "apache-2.0", "model/MODEL_CARD.json": "apache-2.0", "parity/golden_v1.json": "apache-2.0"}
man = P.write_manifest(OUT, files, {"mode": MODE, "repo_commit": GIT, "stage": "export"})
print(json.dumps({k: v["sha256"][:12] for k, v in man["files"].items()}, indent=1))'''),
]


def build(cells, name):
    nb = nbf.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.cells = [nbf.v4.new_markdown_cell(c) if k == "md" else nbf.v4.new_code_cell(c) for k, c in cells]
    nbf.write(nb, Path(__file__).resolve().parent.parent / "notebooks" / name)


if __name__ == "__main__":
    (Path(__file__).resolve().parent.parent / "notebooks").mkdir(exist_ok=True)
    build(NB1, "01_build_hybrid_dataset.ipynb")
    build(NB2, "02_train_and_ablation.ipynb")
    build(NB3, "03_export_onnx_and_parity.ipynb")
