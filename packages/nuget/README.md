# SqlToViz .NET alpha
Targets .NET 8 and 10. Deterministic preview, four statistical detectors, DataTable and dictionary inputs, ApexCharts configuration. Model-backed engine with experimental candidate ONNX models: see below (package `SqlToViz.Onnx`). No SQL execution. Full feature extraction and parity remain pending.

Run dotnet test SqlToViz.Tests/SqlToViz.Tests.csproj and dotnet pack SqlToViz/SqlToViz.csproj -c Release.

## Typed inputs / Entradas tipadas

Pass a `DataTable` directly, or supply typed rows with an explicit projection.
Both use the same deterministic preview and require scalar values in every row.

Pasa un `DataTable` directamente o proyecta filas tipadas de forma explícita.
Ambas entradas usan la misma vista previa determinista y requieren valores
escalares en cada fila.

```csharp
var sales = new[] { (Category: "A", Amount: 10m), (Category: "B", Amount: 20m) };
var plan = SqlToViz.Preview.Recommend("SELECT category, amount", sales,
    row => new Dictionary<string, object?>
    {
        ["category"] = row.Category,
        ["amount"] = row.Amount,
    });
```

## Model-backed engine (experimental)

```csharp
using SqlToViz; using SqlToViz.Onnx;                           // dotnet add package SqlToViz.Onnx
var engine = OnnxEngine.LoadDefault();                          // bundled EXPERIMENTAL candidate models, checksum-verified
var rec = engine.Recommend("SELECT dept, SUM(sal) AS total FROM emp GROUP BY dept",
    new[] { new ColumnSpec("dept"), new ColumnSpec("total") },
    new[] { (IReadOnlyList<object?>)new object?[] { "a", 10.0 }, new object?[] { "b", 20.0 }, new object?[] { "c", 5.0 } });
rec.FinalClass; rec.ModelStatus; rec.Roles; rec.Warnings;
```
`FeatureExtractor.Extract` (package `SqlToViz`, no dependencies) computes the 32 table and 28 column features of SqlVizSpec-v1.0.0; `Engine` takes any `IModelRunner`, and `SqlToViz.Onnx` provides `OnnxRunner` (SHA256 + tensor-schema validated, single-thread CPU). The bundled models are **candidates** (chart: synthetic labels; role: 322 Vega-Lite columns) and every result says `ModelStatus: "experimental"`. Final models drop in with `OnnxEngine.LoadFromDirectory(dir)` (a `manifest.json` with file/sha256/status) - the API and result shape do not change. SQL is never executed.
