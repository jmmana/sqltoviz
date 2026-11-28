// Runs golden fixtures through the SqlToViz / SqlToViz.Onnx .nupkg files restored from a local feed. Args: GOLDEN OUT
using System.Text.Json;
using SqlToViz;
using SqlToViz.Onnx;

static object? Cell(JsonElement e) => e.ValueKind switch {
  JsonValueKind.Null => null, JsonValueKind.String => e.GetString(), JsonValueKind.True => true, JsonValueKind.False => false,
  JsonValueKind.Number => e.GetRawText().IndexOfAny(new[] { '.', 'e', 'E' }) < 0 && e.TryGetInt64(out var l) ? l : e.GetDouble(),
  JsonValueKind.Array => e.EnumerateArray().Select(Cell).ToList(),
  _ => throw new ArgumentException("unsupported json value") };
using var g = JsonDocument.Parse(File.ReadAllText(args[0]));
var engine = OnnxEngine.LoadDefault();
var cases = new Dictionary<string, object>();
foreach (var c in g.RootElement.GetProperty("cases").EnumerateArray()) {
  var id = c.GetProperty("case_id").GetString()!;
  var schema = c.GetProperty("schema").EnumerateArray().Select(s => new ColumnSpec(s.GetProperty("name").GetString()!, s.TryGetProperty("type", out var t) ? t.GetString() : null)).ToList();
  var rows = c.GetProperty("rows").EnumerateArray().Select(r => (IReadOnlyList<object?>)r.EnumerateArray().Select(Cell).ToList()).ToList();
  try {
    var r = engine.Recommend(c.GetProperty("sql").GetString()!, schema, rows);
    cases[id] = new Dictionary<string, object?> {
      ["model_status"] = r.ModelStatus, ["base_class"] = r.BaseClass, ["final_class"] = r.FinalClass, ["rule_class"] = r.RuleClass,
      ["constraint_changed"] = r.ConstraintChanged, ["eligible"] = r.Eligible,
      ["scores"] = Contract.BaseClasses.Select(k => r.Scores![k]).ToArray(),
      ["roles"] = r.Roles!.Select(x => x.Role).ToArray(), ["role_scores"] = r.Roles!.Select(x => x.Scores).ToArray() };
  } catch (FeatureException) { cases[id] = new Dictionary<string, object?> { ["rejected"] = true }; }
}
var asm = typeof(OnnxEngine).Assembly.GetName();
File.WriteAllText(args[1], JsonSerializer.Serialize(new { package = $"{asm.Name} {asm.Version}", models = new Dictionary<string, string>(), cases }));
