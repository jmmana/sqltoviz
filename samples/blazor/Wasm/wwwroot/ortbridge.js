// Bridge from Blazor WASM to onnxruntime-web (WASM EP, single thread: no COOP/COEP headers needed).
import * as ort from './ort/ort.wasm.min.mjs';
ort.env.wasm.wasmPaths = new URL('./ort/', import.meta.url).href;
ort.env.wasm.numThreads = 1;
const sessions = new Map();
async function sha256Hex(buf) {
  const d = await crypto.subtle.digest('SHA-256', buf);
  return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, '0')).join('');
}
export async function load(name, url, expectedSha256, inputName) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`model fetch failed: ${resp.status}`);
  const buf = await resp.arrayBuffer();
  const actual = await sha256Hex(buf);
  if (actual !== expectedSha256) throw new Error(`model checksum mismatch for ${name}`);
  sessions.set(name, { s: await ort.InferenceSession.create(new Uint8Array(buf), { executionProviders: ['wasm'] }), inputName });
}
export async function run(name, data, rows, cols) {
  const { s, inputName } = sessions.get(name);
  const out = await s.run({ [inputName]: new ort.Tensor('float32', Float32Array.from(data), [rows, cols]) });
  return Array.from(Object.values(out)[0].data);
}
