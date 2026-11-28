#!/usr/bin/env python3
"""Verify bundled ONNX model metadata, checksums and license records (#101). Exit 1 on any failure."""
import hashlib, json, pathlib, sys

R = pathlib.Path(__file__).resolve().parents[2]
CAND = R / "model/candidate"
COPIES = [R / "packages/python/sqltoviz/models", R / "packages/npm/models", R / "packages/nuget/SqlToViz.Onnx/models"]
errors = []


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check(cond, msg):
    if not cond:
        errors.append(msg)


contract = sha(R / "spec/sqlvizspec-v1-features.json")
cards = {n: json.loads((CAND / f).read_text()) for n, f in (("chart", "MODEL_CARD.json"), ("role", "ROLE_MODEL_CARD.json"))}
sums = dict(reversed(l.split("  ", 1)) for l in (CAND / "CHECKSUMS.sha256").read_text().splitlines() if l.strip())
for fname, h in sums.items():
    check((CAND / fname).exists() and sha(CAND / fname) == h, f"CHECKSUMS mismatch: {fname}")
check("LICENSE_METADATA.json" in sums, "LICENSE_METADATA.json missing from CHECKSUMS.sha256")
for n, c in cards.items():
    check(c["contract_sha256"] == contract, f"{n} card contract_sha256 != spec")
    check(str(c["status"]).startswith("CANDIDATE"), f"{n} card status must be CANDIDATE")
    check(c["onnx_sha256"] == sha(CAND / f"{n}_model_candidate.onnx"), f"{n} card onnx_sha256 != file")

lic = json.loads((CAND / "LICENSE_METADATA.json").read_text())
for f, m in lic["models"].items():
    check(m["model_status"] == "experimental", f"{f}: license metadata must say experimental")
    check(m["weights_license"] == "undecided", f"{f}: weights license changed - update docs/release/MODEL_LICENSES.md and this check")
check("synthetic" in cards["chart"]["trained_on"], "chart card must state synthetic training")
check("BSD-3-Clause" in cards["role"]["trained_on"], "role card must record the BSD-3-Clause source")

reference = None
for d in COPIES:
    man = json.loads((d / "manifest.json").read_text())
    reference = reference or man
    check(man == reference, f"{d}: manifest differs between packages")
    check(man["contract_sha256"] == contract, f"{d}: manifest contract_sha256 != spec")
    for k in ("chart", "role"):
        e = man[k]
        check(e["status"] == "experimental", f"{d}: {k} status not experimental")
        check(sha(d / e["file"]) == e["sha256"], f"{d}: {k} sha256 != manifest")
        check(e["sha256"] == cards[k]["onnx_sha256"], f"{d}: {k} manifest sha != model card")
        check(sha(d / e["file"]) == sha(CAND / e["file"]), f"{d}: {k} binary differs from model/candidate")

if errors:
    print("FAIL"); [print(" -", e) for e in errors]; sys.exit(1)
print("OK: 2 models x (candidate + 3 package copies) share SHA-256 with cards/manifests; all marked experimental;")
print("    contract hash matches spec; weights license recorded as UNDECIDED (not redistributable-by-license-claim).")
