// Browser WASM entry: `import {createWebRunner} from "@sqltoviz/core/web"` (needs `onnxruntime-web`; also works in Node for tests).
import { Engine } from "./engine.js";
import { verifiedSession } from "./onnx-common.js";
export { ModelError } from "./onnx-common.js";
async function getOrt(o) {
    if (o.ort)
        return o.ort;
    const name = "onnxruntime-web";
    let ort;
    try {
        ort = await import(name);
    }
    catch {
        throw new Error("onnxruntime-web is required for WASM inference: npm install onnxruntime-web");
    }
    return ort;
}
/** `source`: URL string or bytes. Single-threaded WASM, checksum- and schema-validated. */
export async function createWebRunner(source, expectedSha256, kind, o = {}) {
    const ort = await getOrt(o);
    ort.env.wasm.numThreads = 1;
    if (o.wasmPaths)
        ort.env.wasm.wasmPaths = o.wasmPaths;
    const bytes = typeof source === "string" ? new Uint8Array(await (await (o.fetch ?? fetch)(source)).arrayBuffer()) : source;
    return verifiedSession(ort, bytes, expectedSha256, kind, { executionProviders: ["wasm"] });
}
/** Engine from a manifest; `baseUrl` is where the .onnx files are hosted (must serve them with CORS if cross-origin). */
export async function loadWebEngine(manifest, baseUrl, o = {}) {
    const u = (f) => baseUrl.replace(/\/?$/, "/") + f;
    const chart = manifest.chart ? await createWebRunner(u(manifest.chart.file), manifest.chart.sha256, "chart", o) : undefined;
    const role = manifest.role ? await createWebRunner(u(manifest.role.file), manifest.role.sha256, "role", o) : undefined;
    return new Engine({ chart, role, chartStatus: manifest.chart?.status });
}
