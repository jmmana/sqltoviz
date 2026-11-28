using System.Text.Json;
using Microsoft.JSInterop;
using SqlToViz;
namespace BlazorProbe;

/// <summary>
/// SqlToViz recommendations in the browser: feature extraction and rules run in C# (WASM), the two EXPERIMENTAL ONNX models run in
/// onnxruntime-web through JS interop. Uses only the public SqlToViz API (no SqlToViz.Onnx, which needs the native runtime).
/// </summary>
public sealed class OrtWebEngine(IJSRuntime js, HttpClient http)
{
    IJSObjectReference? module;
    sealed class Fixed(float[] output) : IModelRunner { public float[] Run(float[] input, int rows, int cols) => output; }

    public async Task InitAsync()
    {
        module = await js.InvokeAsync<IJSObjectReference>("import", "./ortbridge.js");
        using var doc = JsonDocument.Parse(await http.GetStringAsync("models/manifest.json"));
        var r = doc.RootElement;
        await module.InvokeVoidAsync("load", "chart", "models/" + r.GetProperty("chart").GetProperty("file").GetString(), r.GetProperty("chart").GetProperty("sha256").GetString(), "table_features");
        await module.InvokeVoidAsync("load", "role", "models/" + r.GetProperty("role").GetProperty("file").GetString(), r.GetProperty("role").GetProperty("sha256").GetString(), "column_features");
    }

    public async Task<Recommendation> RecommendAsync(string sql, IReadOnlyList<ColumnSpec> columns, IReadOnlyList<IReadOnlyList<object?>> rows)
    {
        var ex = FeatureExtractor.Extract(sql, columns, rows);
        var chart = await module!.InvokeAsync<float[]>("run", "chart", ex.Table, 1, 32);
        var flat = new float[ex.Columns.Length * 28];
        for (int j = 0; j < ex.Columns.Length; j++) ex.Columns[j].CopyTo(flat, j * 28);
        var role = await module!.InvokeAsync<float[]>("run", "role", flat, ex.Columns.Length, 28);
        return new Engine(new Fixed(chart), new Fixed(role), "experimental").Recommend(sql, columns, rows);
    }
}
