// Browser WASM entry: `import {createWebRunner} from "sqltoviz/web"` (needs `onnxruntime-web`; also works in Node for tests).
import {Engine, type ModelManifest} from "./engine.js";
import {verifiedSession, type ModelKind} from "./onnx-common.js";
export {ModelError} from "./onnx-common.js";

export interface WebOptions { ort?: any; wasmPaths?: string; fetch?: typeof fetch }
async function getOrt(o: WebOptions) {
  if (o.ort) return o.ort;
  const name = "onnxruntime-web";
  let ort: any;
  try { ort = await import(name); } catch { throw new Error("onnxruntime-web is required for WASM inference: npm install onnxruntime-web"); }
  return ort;
}
/** `source`: URL string or bytes. Single-threaded WASM, checksum- and schema-validated. */
export async function createWebRunner(source: string | Uint8Array, expectedSha256: string, kind: ModelKind, o: WebOptions = {}) {
  const ort = await getOrt(o);
  ort.env.wasm.numThreads = 1;
  if (o.wasmPaths) ort.env.wasm.wasmPaths = o.wasmPaths;
  const bytes = typeof source === "string" ? new Uint8Array(await (await (o.fetch ?? fetch)(source)).arrayBuffer()) : source;
  return verifiedSession(ort, bytes, expectedSha256, kind, {executionProviders: ["wasm"]});
}
/** Engine from a manifest; `baseUrl` is where the .onnx files are hosted (must serve them with CORS if cross-origin). */
export async function loadWebEngine(manifest: ModelManifest, baseUrl: string, o: WebOptions = {}): Promise<Engine> {
  const u = (f: string) => baseUrl.replace(/\/?$/, "/") + f;
  const chart = manifest.chart ? await createWebRunner(u(manifest.chart.file), manifest.chart.sha256, "chart", o) : undefined;
  const role = manifest.role ? await createWebRunner(u(manifest.role.file), manifest.role.sha256, "role", o) : undefined;
  return new Engine({chart, role, chartStatus: manifest.chart?.status});
}
export {specializeOutputs, resolveColumns, normalizeOutput, type OutputsResult} from "./outputs.js";
