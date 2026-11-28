#!/usr/bin/env bash
# Copies onnxruntime-web runtime files and the bundled candidate models into the WASM sample's wwwroot (not committed).
set -euo pipefail
cd "$(dirname "$0")"
npm ci --silent
W=../Wasm/wwwroot
mkdir -p "$W/ort" "$W/models"
D=node_modules/onnxruntime-web/dist
cp "$D/ort.wasm.min.mjs" "$D/ort-wasm-simd-threaded.mjs" "$D/ort-wasm-simd-threaded.wasm" "$W/ort/"
cp ../../../packages/nuget/SqlToViz.Onnx/models/*.onnx ../../../packages/nuget/SqlToViz.Onnx/models/manifest.json "$W/models/"
