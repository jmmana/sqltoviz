using System.Text.Json;
using SqlToViz;
namespace SqlToViz.Tests;
internal static class Golden {
  public static JsonDocument Load() {
    var d = new DirectoryInfo(AppContext.BaseDirectory);
    while (d != null) { var p = Path.Combine(d.FullName, "parity", "golden_v1.json"); if (File.Exists(p)) return JsonDocument.Parse(File.ReadAllText(p)); d = d.Parent; }
    throw new FileNotFoundException("parity/golden_v1.json");
  }
  public static string RepoFile(params string[] parts) {
    var d = new DirectoryInfo(AppContext.BaseDirectory);
    while (d != null) { if (File.Exists(Path.Combine(d.FullName, "parity", "golden_v1.json"))) return Path.Combine(new[] { d.FullName }.Concat(parts).ToArray()); d = d.Parent; }
    throw new FileNotFoundException("repo root");
  }
  public static object? Cell(JsonElement e) => e.ValueKind switch {
    JsonValueKind.Null => null, JsonValueKind.String => e.GetString(), JsonValueKind.True => true, JsonValueKind.False => false,
    JsonValueKind.Number => e.GetRawText().IndexOfAny(new[] { '.', 'e', 'E' }) < 0 && e.TryGetInt64(out var l) ? l : e.GetDouble(),
    JsonValueKind.Array => e.EnumerateArray().Select(Cell).ToList(),
    _ => throw new ArgumentException("unsupported json value") };
  public static List<ColumnSpec> Schema(JsonElement c) => c.GetProperty("schema").EnumerateArray().Select(s => new ColumnSpec(s.GetProperty("name").GetString()!, s.TryGetProperty("type", out var t) ? t.GetString() : null)).ToList();
  public static List<IReadOnlyList<object?>> Rows(JsonElement c) => c.GetProperty("rows").EnumerateArray().Select(r => (IReadOnlyList<object?>)r.EnumerateArray().Select(Cell).ToList()).ToList();
  public static bool Close(double a, double b, double atol, double rtol) => Math.Abs(a - b) <= atol + rtol * Math.Abs(b);
  public static double[] Doubles(JsonElement e) => e.EnumerateArray().Select(v => v.GetDouble()).ToArray();
}
