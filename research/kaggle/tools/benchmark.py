"""Latency, memory and size benchmark of the Python reference pipeline (feature extraction + ONNX + constraints).
Usage: benchmark.py CHART_ONNX ROLE_ONNX OUT_JSON [reps]
Single-threaded ONNX session; latency = wall-clock perf_counter after warm-up; memory = peak-RSS growth in a fresh process per size.
Measures THIS reference implementation on THIS machine only (not the TypeScript/.NET SDKs)."""
import json, os, platform, random, resource, subprocess, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from sqltoviz_data import features as F, onnx_export as OX, rules as R

SQL = "SELECT category, region, SUM(value) AS value, day FROM t GROUP BY category, region, day ORDER BY day"
SCHEMA = [{"name": "category"}, {"name": "region"}, {"name": "value"}, {"name": "day"}]
SIZES = (10, 100, 1000, 10000)


def make_rows(n, seed=0):
    r = random.Random(seed)
    return [[f"cat{r.randint(0, 11)}", f"reg{r.randint(0, 4)}", round(r.uniform(0, 1000), 2), f"2024-{1 + i % 12:02d}-{1 + i % 27:02d}"] for i in range(n)]


def opts():
    import onnxruntime as ort
    o = ort.SessionOptions(); o.intra_op_num_threads = 1; o.inter_op_num_threads = 1
    return o


def pct(a, q):
    return float(np.percentile(a, q) * 1000)


def one_run(sess, rows):
    t0 = time.perf_counter(); t, c = F.extract(SQL, SCHEMA, rows); t1 = time.perf_counter()
    s = sess.run(["chart_scores"], {"table_features": t[None, :]})[0][0]; t2 = time.perf_counter()
    R.constrained_choice(s, t, c); t3 = time.perf_counter()
    return t1 - t0, t2 - t1, t3 - t2


if len(sys.argv) > 1 and sys.argv[1] == "--child":
    import onnxruntime as ort
    n, chart = int(sys.argv[2]), sys.argv[3]
    sess = ort.InferenceSession(chart, opts(), providers=["CPUExecutionProvider"]); rows = make_rows(n)
    one_run(sess, rows)
    base = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    for _ in range(30): one_run(sess, rows)
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps({"baseline_rss_bytes": base if sys.platform == "darwin" else base * 1024, "peak_rss_bytes": peak if sys.platform == "darwin" else peak * 1024}))
    sys.exit(0)

chart, role, out = sys.argv[1:4]
reps = int(sys.argv[4]) if len(sys.argv) > 4 else 500
import onnxruntime as ort
sess = ort.InferenceSession(chart, opts(), providers=["CPUExecutionProvider"])
cpu = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip() or platform.processor()
rep = {"environment": {"machine": platform.machine(), "cpu": cpu, "os": platform.platform(), "python": platform.python_version(),
                       "onnxruntime": ort.__version__, "numpy": np.__version__, "threads": 1, "note": "reference Python implementation only"},
       "model_files_bytes": {"chart_model": os.path.getsize(chart), "role_model": os.path.getsize(role) if os.path.exists(role) else None},
       "meta": {"contract_sha256": F.CONTRACT_SHA256, "reps": reps}, "sizes": {}}
for n in SIZES:
    rows = make_rows(n)
    k = reps if n <= 1000 else max(reps // 5, 50)
    for _ in range(20): one_run(sess, rows)
    ex, inf, con = zip(*[one_run(sess, rows) for _ in range(k)])
    tot = np.array(ex) + np.array(inf) + np.array(con)
    mem = json.loads(subprocess.run([sys.executable, __file__, "--child", str(n), chart], capture_output=True, text=True).stdout)
    rep["sizes"][str(n)] = {"runs": k, "extract_ms": {"median": pct(ex, 50), "p95": pct(ex, 95), "p99": pct(ex, 99)},
                            "onnx_ms": {"median": pct(inf, 50), "p95": pct(inf, 95)}, "constraints_ms": {"median": pct(con, 50)},
                            "end_to_end_ms": {"median": pct(tot, 50), "p95": pct(tot, 95), "p99": pct(tot, 99)},
                            "rss_growth_mb": (mem["peak_rss_bytes"] - mem["baseline_rss_bytes"]) / 1e6, "peak_rss_mb": mem["peak_rss_bytes"] / 1e6}
json.dump(rep, open(out, "w"), indent=1)
print(json.dumps({"model_files_bytes": rep["model_files_bytes"], **{n: {k: (v["end_to_end_ms"]["median"], v["end_to_end_ms"]["p95"], v["rss_growth_mb"]) for k, v in [("e2e_median_p95_ms_rss_growth_mb", d)]} for n, d in rep["sizes"].items()}}, indent=1))
