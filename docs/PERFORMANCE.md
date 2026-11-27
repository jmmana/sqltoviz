# SDK performance (Python, TypeScript/Node, .NET)

Measured with `benchmarks/bench_*` on one machine (Apple M4 Pro, macOS-26.5.1-arm64-arm-64bit); single-threaded ONNX Runtime; the same four-column result set per scenario (deterministic rows: nominal x2, quantitative, ISO date), the same candidate chart model. Latency = wall-clock per call after 20 warm-up calls, 400 runs (50 for 10,000 rows); median / p95. **These numbers describe this hardware and these implementations only**; browsers/WASM and other CPUs were not measured here.

## Load time (cold, includes JIT / session creation)

| SDK | runtime | engine load (checksum + 2 ONNX sessions) |
|---|---|---|
| Python | CPython 3.12.13 | 63 ms |
| TypeScript (Node) | Node v24.4.1 | 113 ms |
| C# (.NET) | .NET 10.0.5 | 82 ms |

Python additionally spends 104 ms importing onnxruntime/numpy (not included above).

## End-to-end (extraction + ONNX + constraints), median / p95 ms

| Rows | Python | TypeScript (Node) | C# (.NET) |
|---|---|---|---|
| 10 | 0.232 / 0.357 | 0.079 / 0.136 | 0.066 / 0.078 |
| 100 | 0.623 / 0.889 | 0.165 / 0.254 | 0.302 / 0.414 |
| 1,000 | 4.659 / 5.057 | 1.051 / 1.458 | 1.142 / 3.939 |
| 10,000 | 45.391 / 47.733 | 9.636 / 13.446 | 12.109 / 14.507 |

## Feature extraction, median / p95 ms

| Rows | Python | TypeScript (Node) | C# (.NET) |
|---|---|---|---|
| 10 | 0.215 / 0.306 | 0.041 / 0.076 | 0.057 / 0.067 |
| 100 | 0.605 / 0.827 | 0.130 / 0.186 | 0.290 / 0.389 |
| 1,000 | 4.631 / 5.033 | 0.999 / 1.366 | 1.130 / 3.918 |
| 10,000 | 45.291 / 47.590 | 9.500 / 12.600 | 12.044 / 14.436 |

## ONNX inference (chart model, batch 1), median / p95 ms

| Rows | Python | TypeScript (Node) | C# (.NET) |
|---|---|---|---|
| 10 | 0.011 / 0.029 | 0.032 / 0.071 | 0.007 / 0.009 |
| 100 | 0.012 / 0.050 | 0.030 / 0.076 | 0.008 / 0.022 |
| 1,000 | 0.016 / 0.056 | 0.035 / 0.102 | 0.012 / 0.055 |
| 10,000 | 0.087 / 0.109 | 0.111 / 0.304 | 0.064 / 0.080 |

## Semantic constraints, median / p95 ms

| Rows | Python | TypeScript (Node) | C# (.NET) |
|---|---|---|---|
| 10 | 0.006 / 0.010 | 0.002 / 0.006 | 0.002 / 0.003 |
| 100 | 0.007 / 0.012 | 0.002 / 0.005 | 0.002 / 0.007 |
| 1,000 | 0.008 / 0.015 | 0.002 / 0.005 | 0.003 / 0.009 |
| 10,000 | 0.019 / 0.037 | 0.008 / 0.012 | 0.006 / 0.008 |

## Memory (peak resident set size of a fresh process after 30 calls; growth over the first call)

| Rows | Python | TypeScript (Node) | C# (.NET) |
|---|---|---|---|
| 10 | 140 MB (+0.0)  | 186 MB (+2.2)  | 191 MB (+2.3)  |
| 100 | 144 MB (+0.0)  | 187 MB (+2.9)  | 201 MB (+8.3)  |
| 1,000 | 141 MB (+0.0)  | 194 MB (+10.8)  | 200 MB (+7.1)  |
| 10,000 | 149 MB (+0.5)  | 271 MB (+67.0)  | 207 MB (+0.1)  |

Peak RSS is dominated by the runtime and ONNX Runtime libraries, not by the data. Model files: chart 5.77 MB, role 0.31 MB (candidates).

## Reading
- Feature extraction dominates end-to-end time from about 1,000 rows (tens of ms at 10,000 rows in Python); ONNX inference stays around 0.1 ms or less (median 0.06-0.11 ms at 10,000 rows), so the model is not the bottleneck.
- Node and .NET are several times faster than Python at 1,000-10,000 rows; at 10 rows all are well under a millisecond.
- Reproduce: `python benchmarks/bench_python.py`, `node benchmarks/bench_node.mjs`, `dotnet run -c Release --project benchmarks/bench_dotnet`, then `python benchmarks/report.py`.
