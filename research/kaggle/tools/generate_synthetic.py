"""Generate the synthetic dataset + manifest + leakage audit. Usage: generate_synthetic.py OUT_DIR N_PER_CLASS SEED"""
import hashlib, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import leakage as L, synthgen as G

out, n, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
os.makedirs(out, exist_ok=True)
items = G.generate(n, seed)
G.assert_no_chart_vocabulary(items)
path = os.path.join(out, f"synthetic_seed{seed}.jsonl")
with open(path, "w") as f:
    for it in items:
        f.write(json.dumps(it, sort_keys=True) + "\n")
sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
t0 = time.time()
rep = L.report(items, seed=0)
rep.update({"generator": "sqltoviz_data.synthgen", "seed": seed, "n_per_class": n, "dataset_sha256": sha,
            "license_namespace": "apache-2.0", "audit_seconds": round(time.time() - t0, 1)})
print(json.dumps(rep, indent=1))
json.dump(rep, open(os.path.join(os.path.dirname(__file__), "..", "reports", f"leakage_audit_seed{seed}.json"), "w"), indent=1)
