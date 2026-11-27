"""Build docs/PERFORMANCE.md from benchmarks/results/{python,node,dotnet}.json. Usage: python benchmarks/report.py"""
import json
from pathlib import Path
root = Path(__file__).resolve().parent
R = {k: json.load(open(root / "results" / f"{k}.json")) for k in ("python", "node", "dotnet")}
names = {"python": "Python", "node": "TypeScript (Node)", "dotnet": "C# (.NET)"}
env = R["python"]["environment"]
L = ["# SDK performance (Python, TypeScript/Node, .NET)", "",
     f"Measured with `benchmarks/bench_*` on one machine ({env['cpu']}, {env['os']}); single-threaded ONNX Runtime; the same four-column result set per scenario "
     "(deterministic rows: nominal x2, quantitative, ISO date), the same candidate chart model. Latency = wall-clock per call after 20 warm-up calls, "
     "400 runs (50 for 10,000 rows); median / p95. **These numbers describe this hardware and these implementations only**; browsers/WASM and other CPUs were not measured here.", "",
     "## Load time (cold, includes JIT / session creation)", "", "| SDK | runtime | engine load (checksum + 2 ONNX sessions) |", "|---|---|---|"]
for k, d in R.items():
    L.append(f"| {names[k]} | {d['environment']['runtime']} | {d['load']['engine_load_ms']:.0f} ms |" + ("" if k != "python" else ""))
L += ["", "Python additionally spends " + f"{R['python']['load']['import_ms']:.0f} ms importing onnxruntime/numpy (not included above).", ""]
for title, key in (("End-to-end (extraction + ONNX + constraints), median / p95 ms", "end_to_end_ms"), ("Feature extraction, median / p95 ms", "extract_ms"),
                   ("ONNX inference (chart model, batch 1), median / p95 ms", "onnx_ms"), ("Semantic constraints, median / p95 ms", "constraints_ms")):
    L += [f"## {title}", "", "| Rows | " + " | ".join(names[k] for k in R) + " |", "|---|" + "---|" * len(R)]
    for n in ("10", "100", "1000", "10000"):
        L.append(f"| {int(n):,} | " + " | ".join(f"{R[k]['sizes'][n][key]['median']:.3f} / {R[k]['sizes'][n][key]['p95']:.3f}" for k in R) + " |")
    L.append("")
L += ["## Memory (peak resident set size of a fresh process after 30 calls; growth over the first call)", "", "| Rows | " + " | ".join(names[k] for k in R) + " |", "|---|" + "---|" * len(R)]
for n in ("10", "100", "1000", "10000"):
    L.append(f"| {int(n):,} | " + " | ".join(f"{R[k]['sizes'][n]['peak_rss_mb']:.0f} MB (+{R[k]['sizes'][n]['rss_growth_mb']:.1f}) " for k in R) + " |")
L += ["", "Peak RSS is dominated by the runtime and ONNX Runtime libraries, not by the data. Model files: chart 5.77 MB, role 0.31 MB (candidates).", "",
      "## Reading", "- Feature extraction dominates end-to-end time from about 1,000 rows (tens of ms at 10,000 rows in Python); ONNX inference stays around 0.1 ms or less (median 0.06-0.11 ms at 10,000 rows), so the model is not the bottleneck.",
      "- Node and .NET are several times faster than Python at 1,000-10,000 rows; at 10 rows all are well under a millisecond.",
      "- Reproduce: `python benchmarks/bench_python.py`, `node benchmarks/bench_node.mjs`, `dotnet run -c Release --project benchmarks/bench_dotnet`, then `python benchmarks/report.py`.", ""]
(root.parent / "docs" / "PERFORMANCE.md").write_text("\n".join(L))
print("\n".join(L[:20]))
