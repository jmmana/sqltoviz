"""SDK benchmark (Python). Output JSON schema is shared by bench_node.mjs and bench_dotnet. Single-threaded ONNX.
Usage: python benchmarks/bench_python.py OUT.json [reps=400]   |   internal: --child N (peak-RSS probe in a fresh process)"""
import json, os, platform, resource, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "python"))
SQL = "SELECT category, region, SUM(value) AS value, day FROM t GROUP BY category, region, day ORDER BY day"
SCHEMA = [{"name": "category"}, {"name": "region"}, {"name": "value"}, {"name": "day"}]
SIZES = (10, 100, 1000, 10000)


def make_rows(n):  # deterministic, identical formula in every language
    return [[f"cat{(i * 7) % 12}", f"reg{(i * 3) % 5}", ((i * 37) % 1000) + ((i * 13) % 100) / 100, f"2024-{1 + i % 12:02d}-{1 + i % 27:02d}"] for i in range(n)]


def pct(a, q):
    a = sorted(a)
    k = (len(a) - 1) * q / 100
    lo = int(k)
    return (a[lo] + (a[min(lo + 1, len(a) - 1)] - a[lo]) * (k - lo)) * 1000


def load():
    import onnxruntime as ort, numpy as np
    from sqltoviz import Engine, features as F, rules
    return ort, np, Engine, F, rules


def one(engine, F, rules, np, rows):
    t0 = time.perf_counter(); table, cols = F.extract(SQL, SCHEMA, rows); t1 = time.perf_counter()
    scores = engine.chart.run(["chart_scores"], {"table_features": np.asarray([table], dtype=np.float32)})[0][0]; t2 = time.perf_counter()
    rules.constrained_choice([float(x) for x in scores], table, cols); t3 = time.perf_counter()
    return t1 - t0, t2 - t1, t3 - t2


if len(sys.argv) > 2 and sys.argv[1] == "--child":
    ort, np, Engine, F, rules = load(); n = int(sys.argv[2]); e = Engine.default(); rows = make_rows(n); one(e, F, rules, np, rows)
    b = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    for _ in range(30): one(e, F, rules, np, rows)
    p = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    k = 1 if sys.platform == "darwin" else 1024
    print(json.dumps({"baseline": b * k, "peak": p * k})); sys.exit(0)

out = sys.argv[1]; reps = int(sys.argv[2]) if len(sys.argv) > 2 else 400
t0 = time.perf_counter(); ort, np, Engine, F, rules = load(); import_ms = (time.perf_counter() - t0) * 1000
t0 = time.perf_counter(); engine = Engine.default(); load_ms = (time.perf_counter() - t0) * 1000
cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip() or platform.processor() or platform.machine()
res = {"sdk": "python", "environment": {"cpu": cpu, "os": platform.platform(), "runtime": f"CPython {platform.python_version()}", "onnxruntime": ort.__version__, "threads": 1},
       "load": {"import_ms": import_ms, "engine_load_ms": load_ms, "note": "Engine.default(): checksum + 2 sessions (cold, first call)"}, "sizes": {}}
for n in SIZES:
    rows = make_rows(n); k = reps if n <= 1000 else max(reps // 8, 40)
    for _ in range(20): one(engine, F, rules, np, rows)
    ex, inf, con = zip(*[one(engine, F, rules, np, rows) for _ in range(k)])
    tot = [a + b + c for a, b, c in zip(ex, inf, con)]
    m = json.loads(subprocess.run([sys.executable, __file__, "--child", str(n)], capture_output=True, text=True).stdout)
    res["sizes"][str(n)] = {"runs": k, "extract_ms": {"median": pct(ex, 50), "p95": pct(ex, 95), "p99": pct(ex, 99)}, "onnx_ms": {"median": pct(inf, 50), "p95": pct(inf, 95)},
                            "constraints_ms": {"median": pct(con, 50), "p95": pct(con, 95)}, "end_to_end_ms": {"median": pct(tot, 50), "p95": pct(tot, 95), "p99": pct(tot, 99)},
                            "peak_rss_mb": m["peak"] / 1e6, "rss_growth_mb": (m["peak"] - m["baseline"]) / 1e6}
json.dump(res, open(out, "w"), indent=1)
print(json.dumps({n: round(d["end_to_end_ms"]["median"], 3) for n, d in res["sizes"].items()}), "load_ms", round(load_ms, 1))
