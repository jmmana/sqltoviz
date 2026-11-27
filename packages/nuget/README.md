# SqlToViz .NET alpha
Targets .NET 8 and 10. Deterministic preview, four statistical detectors, DataTable and dictionary inputs, ApexCharts configuration. No native ONNX or Blazor WASM validation yet. No SQL execution. Full feature extraction and parity remain pending.

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
