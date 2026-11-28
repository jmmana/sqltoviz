#!/usr/bin/env python3
"""Compare a runner output with parity/golden_v1.json. Usage: compare.py GOLDEN RESULT LABEL"""
import json, pathlib, sys

golden = json.load(open(sys.argv[1]))
res = json.load(open(sys.argv[2]))
label = sys.argv[3]
atol, rtol = golden["atol"], golden["rtol"]
close = lambda a, b: abs(a - b) <= atol + rtol * abs(b)
bad, acc, rej = [], 0, 0
manifest = json.load(open(pathlib.Path(__file__).resolve().parents[3] / "packages/npm/models/manifest.json"))
for k in ("chart", "role"):
    got = res["models"].get(manifest[k]["file"])
    if res["models"] and got != manifest[k]["sha256"]:
        bad.append(f"installed {k} model sha {got} != manifest {manifest[k]['sha256']}")
for c in golden["cases"]:
    cid, e, r = c["case_id"], c["expected"], res["cases"].get(c["case_id"])
    if r is None:
        bad.append(f"{cid}: missing"); continue
    if e.get("rejected"):
        (rej := rej + 1) if r.get("rejected") else bad.append(f"{cid}: should be rejected"); continue
    if r.get("rejected"):
        bad.append(f"{cid}: unexpectedly rejected"); continue
    acc += 1
    if r["model_status"] != "experimental": bad.append(f"{cid}: model_status {r['model_status']}")
    for f in ("base_class", "final_class", "rule_class", "constraint_changed", "eligible", "roles"):
        if r[f] != e[f]: bad.append(f"{cid}: {f}")
    if not all(close(a, b) for a, b in zip(r["scores"], e["chart_scores"])) or len(r["scores"]) != 10: bad.append(f"{cid}: chart scores")
    if len(r["role_scores"]) != len(e["role_scores"]) or not all(close(a, b) for x, y in zip(r["role_scores"], e["role_scores"]) for a, b in zip(x, y)): bad.append(f"{cid}: role scores")
print(f"[{label}] package={res['package']} accepted={acc} rejected={rej} failures={len(bad)}")
for b in bad[:15]: print("  -", b)
sys.exit(1 if bad or acc < 275 or rej < 10 else 0)
