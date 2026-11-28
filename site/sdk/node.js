// Node.js ONNX runtime entry: `import {loadDefaultEngine, createNodeRunner} from "@sqltoviz/core/node"` (needs `onnxruntime-node`).
import { readFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { Engine } from "./engine.js";
import { verifiedSession } from "./onnx-common.js";
export { ModelError } from "./onnx-common.js";
/** Directory of the bundled EXPERIMENTAL candidate models (replace the files/manifest there, or pass your own paths). */
export const bundledModelsDir = () => resolve(dirname(fileURLToPath(import.meta.url)), "..", "..", "models");
export async function createNodeRunner(path, expectedSha256, kind) {
    const name = "onnxruntime-node";
    let ort;
    try {
        ort = await import(name);
    }
    catch (e) {
        throw new Error("onnxruntime-node is required for Node inference: npm install onnxruntime-node");
    }
    const bytes = new Uint8Array(await readFile(path));
    return verifiedSession(ort, bytes, expectedSha256, kind, { executionProviders: ["cpu"], intraOpNumThreads: 1, interOpNumThreads: 1 });
}
/** Engine from a manifest ({chart?, role?} with file/sha256/status) and the directory holding the files. */
export async function loadEngine(manifest, dir) {
    const chart = manifest.chart ? await createNodeRunner(join(dir, manifest.chart.file), manifest.chart.sha256, "chart") : undefined;
    const role = manifest.role ? await createNodeRunner(join(dir, manifest.role.file), manifest.role.sha256, "role") : undefined;
    return new Engine({ chart, role, chartStatus: manifest.chart?.status });
}
/** Engine with the bundled EXPERIMENTAL candidate models (checksum-verified). */
export async function loadDefaultEngine(dir = bundledModelsDir()) {
    return loadEngine(JSON.parse(await readFile(join(dir, "manifest.json"), "utf8")), dir);
}
