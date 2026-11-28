# SqlToViz with Blazor Server and Blazor WebAssembly

Status: alpha. The bundled ONNX models are **experimental candidates** (chart: synthetic labels; role: 322 Vega-Lite columns). No human validation exists; every result reports `ModelStatus: "experimental"`. Nothing here claims recommendation quality; it only documents which hosting strategies run.

Everything below was built and executed with the sample projects in [`samples/blazor`](../samples/blazor) (.NET SDK 10.0.5, Blazor templates for net10.0, headless Chromium via Playwright, macOS arm64, 2026-11-27). CI (`.github/workflows/blazor-ci.yml`) repeats the Server and WASM runs on Linux.

## What works (verified)

| Host | Option | Result |
|---|---|---|
| Blazor Server | `SqlToViz` + `SqlToViz.Onnx` (`OnnxEngine.LoadDefault()`), native ONNX Runtime | Works. Models load (checksum verified) and run. Same API as any .NET app. |
| Blazor WebAssembly | `SqlToViz` only: `new Engine()` (rules only) and `Preview.Recommend` | Works. Pure managed code. `ModelStatus` is `none (rules only)`, so the recommendation is the deterministic rule class. |
| Blazor WebAssembly | `SqlToViz` + `SqlToViz.Onnx` | **Builds and publishes, fails at runtime.** `OnnxEngine.LoadDefault()` throws `TypeInitializationException` in `Microsoft.ML.OnnxRuntime.NativeMethods`: the NuGet package ships native libraries for desktop/mobile RIDs, not for `browser-wasm`. It also adds about 6 MB of embedded models to the payload for nothing. Do not reference `SqlToViz.Onnx` from a WASM project. |
| Blazor WebAssembly | `SqlToViz` + `onnxruntime-web` through JS interop | Works (prototype in `samples/blazor/Wasm`: `ortbridge.js`, `OrtWebEngine.cs`). C# runs `FeatureExtractor.Extract`, JS runs the two ONNX models (WASM execution provider, single thread), C# applies `Rules`/`Engine`. |

Equivalence check: for three inputs (KPI, a 3-row dimension plus measure, a 4-row temporal series) the Server (native ORT) and WASM (onnxruntime-web) hosts produced the same `FinalClass`/`BaseClass` and identical chart scores to 4 decimals (`final=kpi`, `donut`, `table`). That is three inputs, not the 308-case golden suite; the golden parity run remains the .NET and TypeScript SDK tests.

## Recommended strategy

1. **Blazor Server, or any server-side .NET host (also the server of a hosted WASM app):** use `SqlToViz.Onnx` as documented. This is the only path with the full .NET API, checksum verification inside the runner and the smallest client download.
2. **Blazor WASM, no models needed:** reference `SqlToViz` only and use `Engine()` (rules) or `Preview`. Smallest payload, no JS.
3. **Blazor WASM with the models:** either (a) call a server endpoint that runs `OnnxEngine` (this sends the query result to your server), or (b) use onnxruntime-web via JS interop as in the sample. Pick (b) when data must stay in the browser and an extra ~11 MB (about 2.9 MB gzip) runtime plus models is acceptable.
4. Alternatively use the TypeScript SDK (`packages/npm`) from JS interop; it already bundles an ONNX path for browsers. That route was not built or tested here.

## Measurements (this machine only)

Published without the `wasm-tools` workload (no AOT, no relinking), default ICU data included, Brotli/gzip files produced by `dotnet publish`.

| Variant | `wwwroot` raw | `wwwroot` Brotli (publish output) |
|---|---|---|
| WASM, `SqlToViz` only (rules) | 18.4 MB | 4.1 MB |
| WASM, + `SqlToViz.Onnx` (does not run) | 24.9 MB | 4.5 MB (the .onnx models are stored inside an assembly and compress well) |
| WASM, `SqlToViz` + onnxruntime-web + models | 36.0 MB | 6.1 MB |

Components of the third variant: `SqlToViz.wasm` 85 KB (30 KB Brotli); `ort-wasm-simd-threaded.wasm` 11.2 MB (2.9 MB with gzip -9; Brotli size not measured separately); chart model 5.77 MB (about 0.32 MB gzip); role model 0.31 MB. The .NET runtime itself (`dotnet.native.wasm` 3.0 MB, `System.Private.CoreLib` 1.7 MB) dominates the rules-only variant.

Headless Chromium on localhost (python static server, warm disk cache, no throttling), one measurement each, so treat as an order of magnitude only: page ready with rules only in about 0.2 s wall time; with onnxruntime-web, `init` (fetch, SHA-256, create two sessions) 275-413 ms and first recommendation 22-30 ms, later ones 2-4 ms (cf. docs/PERFORMANCE.md for the TypeScript SDK in Chromium). Native Server: `LoadDefault()` 41-70 ms warm (866 ms on the first cold process start), run 0.2-3 ms.

## Not measured / limitations

- Real network transfer time, mobile CPUs, other browsers (only Chromium), memory use, and AOT/trimmed builds (`wasm-tools` was not installed) were not measured.
- onnxruntime-web is run single-threaded (no cross-origin isolation headers needed); multithreading and WebGPU were not tried.
- The WASM prototype copies model files and checks their SHA-256 in JS; it does not use `SqlToViz.Onnx` and is sample code, not a packaged API.
- MudBlazor and ApexCharts adapters (`SqlToViz.MudBlazor`) only produce chart models; no rendering test in a browser was done.
- Model quality is unknown: see `docs/PERFORMANCE.md` and `research/kaggle/EXPERIMENTS.md` for what has (and has not) been measured.

## Reproduce

```bash
cd samples/blazor/tools && ./prepare.sh && npx playwright install chromium
dotnet publish ../Server -c Release -o ../out/server && node check.mjs server ../out/server
dotnet publish ../Wasm   -c Release -o ../out/wasm   && node check.mjs wasm ../out/wasm/wwwroot ort
# the failing variant: dotnet publish ../Wasm -c Release -p:WithOnnx=true -o ../out/wasm-onnx
```
