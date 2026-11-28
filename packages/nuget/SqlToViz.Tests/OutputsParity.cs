using System.Text.Json;
using Xunit;
namespace SqlToViz.Tests;
// Replays parity/outputs_v1.json (SqlVizSpec-Outputs-v1.0.0). Expectations come from the Python reference: this proves cross-runtime agreement, not that the rules are right.
public class OutputsParity {
  static object? Val(JsonElement e) => e.ValueKind switch {
    JsonValueKind.Object => e.EnumerateObject().ToDictionary(p => p.Name, p => Val(p.Value)) as IReadOnlyDictionary<string, object?>,
    JsonValueKind.Array => e.EnumerateArray().Select(Val).ToList() as IReadOnlyList<object?>,
    _ => Golden.Cell(e) };

  static void Same(string id, string path, JsonElement exp, object? act, double atol, double rtol, bool exact, List<string> bad) {
    switch (exp.ValueKind) {
      case JsonValueKind.Null: if (act is not null) bad.Add($"{id} {path}: expected null got {act}"); break;
      case JsonValueKind.String: if (act as string != exp.GetString()) bad.Add($"{id} {path}: expected {exp.GetString()} got {act}"); break;
      case JsonValueKind.Number:
        if (act is null or string or bool) { bad.Add($"{id} {path}: expected number got {act}"); break; }
        double a = Convert.ToDouble(act, System.Globalization.CultureInfo.InvariantCulture), b = exp.GetDouble();
        if (exact ? a != b : !Golden.Close(a, b, atol, rtol)) bad.Add($"{id} {path}: {a} vs {b}"); break;
      case JsonValueKind.Array:
        if (act is not System.Collections.IList l || l.Count != exp.GetArrayLength()) { bad.Add($"{id} {path}: array mismatch"); break; }
        int i = 0; foreach (var x in exp.EnumerateArray()) { Same(id, $"{path}[{i}]", x, l[i], atol, rtol, exact, bad); i++; } break;
      case JsonValueKind.Object:
        if (act is not System.Collections.IDictionary d || d.Count != exp.EnumerateObject().Count()) { bad.Add($"{id} {path}: object keys {(act as System.Collections.IDictionary)?.Count} vs {exp.EnumerateObject().Count()}"); break; }
        foreach (var p in exp.EnumerateObject()) { if (!d.Contains(p.Name)) bad.Add($"{id} {path}: missing {p.Name}"); else Same(id, path + "." + p.Name, p.Value, d[p.Name], atol, rtol, exact, bad); }
        break;
      default: bad.Add($"{id} {path}: unsupported"); break;
    }
  }

  [Fact] public void FixturePinsMatchContract() {
    using var f = JsonDocument.Parse(File.ReadAllText(Golden.RepoFile("parity", "outputs_v1.json")));
    Assert.Equal(OutputsContract.Sha256, f.RootElement.GetProperty("outputs_sha256").GetString());
    Assert.Equal(Contract.Sha256, OutputsContract.BaseContractSha256);
    Assert.Equal(OutputsContract.BaseContractSha256, f.RootElement.GetProperty("base_contract_sha256").GetString());
    var sha = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(Golden.RepoFile("spec", "sqlvizspec-v1-outputs.json")))).ToLowerInvariant();
    Assert.Equal(sha, OutputsContract.Sha256);
  }

  [Fact] public void AllOutputsCasesReplay() {
    using var f = JsonDocument.Parse(File.ReadAllText(Golden.RepoFile("parity", "outputs_v1.json")));
    var root = f.RootElement; double atol = root.GetProperty("atol").GetDouble(), rtol = root.GetProperty("rtol").GetDouble();
    var bad = new List<string>(); int n = 0;
    foreach (var c in root.GetProperty("cases").EnumerateArray()) {
      var id = c.GetProperty("id").GetString()!;
      var cols = c.GetProperty("columns").EnumerateArray().Select(s => new ColumnSpec(s.GetProperty("name").GetString()!, s.TryGetProperty("type", out var t) && t.ValueKind == JsonValueKind.String ? t.GetString() : null)).ToList();
      var rows = Golden.Rows(c);
      var meta = c.GetProperty("metadata").ValueKind == JsonValueKind.Object ? (IReadOnlyDictionary<string, object?>)Val(c.GetProperty("metadata"))! : null;
      var sc = c.GetProperty("base_scores"); var scores = sc.ValueKind == JsonValueKind.Object ? sc.EnumerateObject().ToDictionary(p => p.Name, p => p.Value.GetDouble()) : null;
      var rl = c.GetProperty("roles"); var roles = rl.ValueKind == JsonValueKind.Object ? rl.EnumerateObject().ToDictionary(p => p.Name, p => p.Value.GetString()!) : null;
      var el = c.GetProperty("base_eligibility").EnumerateObject().ToDictionary(p => p.Name, p => p.Value.GetBoolean());
      var exp = c.GetProperty("expected");
      OutputResult r;
      try { r = Outputs.SpecializeOutputs(cols, rows, meta, scores, roles, el); } catch (Exception e) { bad.Add($"{id}: threw {e.GetType().Name} {e.Message}"); continue; }
      if (r.Output != exp.GetProperty("output").GetString()) bad.Add($"{id}: output {r.Output} vs {exp.GetProperty("output").GetString()}");
      Same(id, "encodings", exp.GetProperty("encodings"), r.Encodings, atol, rtol, true, bad);
      Same(id, "fallback_chain", exp.GetProperty("fallback_chain"), r.FallbackChain, atol, rtol, true, bad);
      var rej = exp.GetProperty("rejected").EnumerateArray().Select(x => x.GetProperty("output").GetString() + ":" + x.GetProperty("reason_code").GetString()).ToList();
      if (!rej.SequenceEqual(r.Rejected.Select(x => x.Output + ":" + x.ReasonCode))) bad.Add($"{id}: rejected differs");
      Same(id, "params", exp.GetProperty("params"), r.Params, atol, rtol, false, bad);
      n++;
    }
    Assert.Empty(bad.Take(15));
    Assert.Equal(root.GetProperty("n_cases").GetInt32(), n);
    Assert.Equal(120, n);
  }

  [Fact] public void LegacyAliasNormalizes() { Assert.Equal("kpi", Outputs.NormalizeOutput("kpi_card")); Assert.Equal("gauge", Outputs.NormalizeOutput("gauge")); }
}
