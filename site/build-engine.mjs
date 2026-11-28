// Copies the built TypeScript SDK, the EXPERIMENTAL candidate ONNX models and the onnxruntime-web WASM runtime into site/ (generated, not committed).
// Prerequisite: (cd packages/npm && npm install --ignore-scripts && npm run build)
import {cpSync, mkdirSync, existsSync, readdirSync, rmSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
const root = join(dirname(fileURLToPath(import.meta.url)), '..'), npm = join(root, 'packages', 'npm'), site = join(root, 'site');
const must = (p) => { if (!existsSync(p)) throw new Error(`missing ${p}: build packages/npm first`); return p; };
for (const d of ['sdk', 'models', 'vendor']) rmSync(join(site, d), {recursive: true, force: true});
mkdirSync(join(site, 'sdk'), {recursive: true}); mkdirSync(join(site, 'vendor', 'ort'), {recursive: true});
for (const f of readdirSync(must(join(npm, 'dist', 'esm')))) if (f.endsWith('.js')) cpSync(join(npm, 'dist', 'esm', f), join(site, 'sdk', f));
cpSync(must(join(npm, 'models')), join(site, 'models'), {recursive: true});
const ort = must(join(npm, 'node_modules', 'onnxruntime-web', 'dist'));
for (const f of ['ort.wasm.min.mjs', 'ort-wasm-simd-threaded.mjs', 'ort-wasm-simd-threaded.wasm']) cpSync(must(join(ort, f)), join(site, 'vendor', 'ort', f));
console.log('site/sdk, site/models and site/vendor/ort ready');
