#!/usr/bin/env bash
# Release-candidate integration test (#102). Never publishes anything.
#   rc_integration.sh build  ARTIFACTS     build wheel, npm tarball and .nupkg files into ARTIFACTS
#   rc_integration.sh test   ARTIFACTS python|node|dotnet   install ONLY the packed artifact into a clean
#                                          environment (outside the repo) and run parity/golden_v1.json through it
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RC="$ROOT/scripts/release/rc"
GOLDEN="$ROOT/parity/golden_v1.json"
cmd="$1"; ART="$(mkdir -p "$2" && cd "$2" && pwd)"

if [ "$cmd" = build ]; then
  (cd "$ROOT/packages/python" && python -m pip install -q build && python -m build --outdir "$ART")
  (cd "$ROOT/packages/npm" && npm ci --ignore-scripts && npm pack --pack-destination "$ART")
  dotnet pack "$ROOT/packages/nuget/SqlToViz/SqlToViz.csproj" -c Release -o "$ART"
  dotnet pack "$ROOT/packages/nuget/SqlToViz.Onnx/SqlToViz.Onnx.csproj" -c Release -o "$ART"
  ls -l "$ART"; exit 0
fi

eco="$3"; WORK="$(mktemp -d)"; OUT="$WORK/result.json"
case "$eco" in
  python)
    python -m venv "$WORK/venv"
    "$WORK/venv/bin/pip" install -q "$ART"/sqltoviz-*.whl onnxruntime numpy   # no -e, no repo on sys.path
    (cd "$WORK" && "$WORK/venv/bin/python" -I "$RC/run_python.py" "$GOLDEN" "$OUT") ;;
  node)
    mkdir "$WORK/app" && cd "$WORK/app" && npm init -y >/dev/null
    npm install --ignore-scripts "$ART"/sqltoviz-core-*.tgz onnxruntime-node@1.31.1 >/dev/null
    cp "$RC/run_node.mjs" . && node run_node.mjs "$GOLDEN" "$OUT" ;;   # script lives beside node_modules so only the installed tarball resolves
  dotnet)
    mkdir "$WORK/app" && cd "$WORK/app"
    TFM="${TFM:-net8.0}"
    cat > app.csproj <<CSPROJ
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>$TFM</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable><RestoreSources>$ART;https://api.nuget.org/v3/index.json</RestoreSources></PropertyGroup>
<ItemGroup><PackageReference Include="SqlToViz.Onnx" Version="0.1.0-alpha.1"/></ItemGroup></Project>
CSPROJ
    cp "$RC/dotnet/Program.cs" .
    dotnet run -c Release -- "$GOLDEN" "$OUT" ;;
  *) echo "unknown ecosystem $eco"; exit 2 ;;
esac
python3 "$RC/compare.py" "$GOLDEN" "$OUT" "$eco"
