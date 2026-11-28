# SDK performance (Python, TypeScript/Node, .NET)

Measured with `benchmarks/bench_*` on one machine (Apple M4 Pro, macOS-26.5.1-arm64-arm-64bit); single-threaded ONNX Runtime; the same four-column result set per scenario (deterministic rows: nominal x2, quantitative, ISO date), the same candidate chart model. Latency = wall-clock per call after 20 warm-up calls, 400 runs (50 for 10,000 rows); median / p95. The browser column times batches of calls (Chromium coarsens `performance.now()` to 0.1 ms) and reports per-call means; its "p95" is over batch means. **These numbers describe this hardware and these implementations only**; browsers/WASM and other CPUs were not measured here.

## Load time (cold, includes JIT / session creation)

| SDK | runtime | engine load (checksum + 2 ONNX sessions) |
|---|---|---|
| Python | CPython 3.12.13 | 63 ms |
| TypeScript (Node) | Node v24.4.1 | 113 ms |
| C# (.NET) | .NET 10.0.5 | 82 ms |
| TypeScript (Chromium WASM) | Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/ | 357 ms |

Python additionally spends 104 ms importing onnxruntime/numpy (not included above).

## End-to-end (extraction + ONNX + constraints), median / p95 ms

| Rows | Python | TypeScript (Node) | C# (.NET) | TypeScript (Chromium WASM) |
|---|---|---|---|---|
| 10 | 0.232 / 0.357 | 0.079 / 0.136 | 0.066 / 0.078 | 0.038 / 0.051 |
| 100 | 0.623 / 0.889 | 0.165 / 0.254 | 0.302 / 0.414 | 0.101 / 0.120 |
| 1,000 | 4.659 / 5.057 | 1.051 / 1.458 | 1.142 / 3.939 | 0.710 / 0.751 |
| 10,000 | 45.391 / 47.733 | 9.636 / 13.446 | 12.109 / 14.507 | 7.500 / 7.905 |

## Feature extraction, median / p95 ms

| Rows | Python | TypeScript (Node) | C# (.NET) | TypeScript (Chromium WASM) |
|---|---|---|---|---|
| 10 | 0.215 / 0.306 | 0.041 / 0.076 | 0.057 / 0.067 | 0.026 / 0.033 |
| 100 | 0.605 / 0.827 | 0.130 / 0.186 | 0.290 / 0.389 | 0.090 / 0.108 |
| 1,000 | 4.631 / 5.033 | 0.999 / 1.366 | 1.130 / 3.918 | 0.700 / 0.736 |
| 10,000 | 45.291 / 47.590 | 9.500 / 12.600 | 12.044 / 14.436 | 7.400 / 7.900 |

## ONNX inference (chart model, batch 1), median / p95 ms

| Rows | Python | TypeScript (Node) | C# (.NET) | TypeScript (Chromium WASM) |
|---|---|---|---|---|
| 10 | 0.011 / 0.029 | 0.032 / 0.071 | 0.007 / 0.009 | 0.012 / 0.019 |
| 100 | 0.012 / 0.050 | 0.030 / 0.076 | 0.008 / 0.022 | 0.010 / 0.012 |
| 1,000 | 0.016 / 0.056 | 0.035 / 0.102 | 0.012 / 0.055 | 0.010 / 0.020 |
| 10,000 | 0.087 / 0.109 | 0.111 / 0.304 | 0.064 / 0.080 | 0.100 / 0.200 |

## Semantic constraints, median / p95 ms

| Rows | Python | TypeScript (Node) | C# (.NET) | TypeScript (Chromium WASM) |
|---|---|---|---|---|
| 10 | 0.006 / 0.010 | 0.002 / 0.006 | 0.002 / 0.003 | 0.000 / 0.002 |
| 100 | 0.007 / 0.012 | 0.002 / 0.005 | 0.002 / 0.007 | 0.000 / 0.002 |
| 1,000 | 0.008 / 0.015 | 0.002 / 0.005 | 0.003 / 0.009 | 0.000 / 0.005 |
| 10,000 | 0.019 / 0.037 | 0.008 / 0.012 | 0.006 / 0.008 | 0.000 / 0.000 |

## Memory (peak resident set size of a fresh process after 30 calls; growth over the first call)

| Rows | Python | TypeScript (Node) | C# (.NET) |
|---|---|---|---|
| 10 | 140 MB (+0.0)  | 186 MB (+2.2)  | 191 MB (+2.3)  |
| 100 | 144 MB (+0.0)  | 187 MB (+2.9)  | 201 MB (+8.3)  |
| 1,000 | 141 MB (+0.0)  | 194 MB (+10.8)  | 200 MB (+7.1)  |
| 10,000 | 149 MB (+0.5)  | 271 MB (+67.0)  | 207 MB (+0.1)  |

Browser memory was not measured (page JS heap is not comparable with process RSS). Peak RSS is dominated by the runtime and ONNX Runtime libraries, not by the data. Model files: chart 5.77 MB, role 0.31 MB (candidates).

## Reading
- Feature extraction dominates end-to-end time from about 1,000 rows (tens of ms at 10,000 rows in Python); ONNX inference stays around 0.1 ms or less (median 0.06-0.11 ms at 10,000 rows), so the model is not the bottleneck.
- Node and .NET are several times faster than Python at 1,000-10,000 rows; at 10 rows all are well under a millisecond.
- Reproduce: `python benchmarks/bench_python.py`, `node benchmarks/bench_node.mjs`, `dotnet run -c Release --project benchmarks/bench_dotnet`, `node benchmarks/bench_browser.mjs` (needs playwright + chromium and `node site/build-engine.mjs`), then `python benchmarks/report.py`.

## Browser playground: bundle size and WASM cold start

Reproduce: `node site/build-engine.mjs && BROWSERS=all node site/e2e/measure.mjs 5` (needs `npm i --no-save playwright@1.65.1 && npx playwright install chromium firefox webkit`). The functional check on the same three engines is `BROWSERS=all node site/e2e/playground.e2e.mjs` (same assertions on each: WASM inference, experimental label, tensor download, zero external requests). Measured 2026-11-27 on Apple M4 Pro / macOS (Darwin 25.5.0), Node 24.4.1, Playwright 1.65.1, single-threaded WASM, local static server (no network latency or CDN compression; the gzip/brotli columns are computed offline from the served files, they are not what a particular host sends).

## Playground payload (served bytes)

| Part | Files | Raw | gzip -9 | brotli q11 |
|---|---|---|---|---|
| onnxruntime-web WASM binary | 1 | 14500.8 KiB | 3703.6 KiB | 2391.8 KiB |
| onnxruntime-web JS (2 files) | 2 | 76.6 KiB | 25.7 KiB | 23.0 KiB |
| ONNX candidate models + manifest | 3 | 5936.5 KiB | 343.6 KiB | 242.1 KiB |
| SDK modules (site/sdk) | 8 | 45.8 KiB | 15.0 KiB | 13.2 KiB |
| Playground code (html/css/mjs, excl. generated) | 11 | 23.6 KiB | 10.6 KiB | 8.9 KiB |
| Engine total (rows 1-4, loaded only on "Run experimental model") | | 20.08 MiB | 3.99 MiB | 2.61 MiB |

## Cold start of the WASM engine (5 fresh contexts per browser; median / min / max ms)

| Browser | version | Playground ready (load event) | Cold: click -> result | Warm: click -> result | Bytes fetched on cold click |
|---|---|---|---|---|---|
| chromium | 159.0.8154.6 | 40 / 34 / 78 | 588 / 560 / 592 | 61 / 54 / 66 | 19.72 MiB |
| firefox | 159.0 | 32 / 31 / 150 | 405 / 383 / 537 | 30 / 29 / 30 | 5.88 MiB |
| webkit | 27.2 | 30 / 28 / 63 | 412 / 384 / 438 | 21 / 16 / 25 | 19.72 MiB |

Reading the numbers:

- The engine (onnxruntime-web WASM + two candidate models + SDK) is only fetched when the user presses "Run experimental model"; the rule-based preview loads about 24 KiB of own code and no WASM.
- Cold start is dominated by fetching and compiling the 14.5 MiB WASM binary and creating two ONNX sessions; after that, a recommendation takes tens of milliseconds end to end including DOM rendering (warm column).
- The Firefox "bytes fetched" figure is not comparable: Playwright does not expose that engine's WASM response body, so the counter undercounts there (5.88 MiB vs the 19.72 MiB the other two report). The static payload table is the authoritative size.
- Times are medians of 5 fresh contexts on one machine and one browser build each; they say nothing about slower CPUs, mobile browsers or real networks (at 20 MiB raw / about 4 MiB gzip the download will dominate there).
- Safari proper was not tested: Playwright WebKit is the engine, not the Safari application.
