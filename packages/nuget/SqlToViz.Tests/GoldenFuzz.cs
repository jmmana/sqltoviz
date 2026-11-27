// Differential fuzz: replays random cases whose expected values were produced by the Python SDK (parity/tools/gen_fuzz.py).
using System.Text.Json;
using SqlToViz;
using Xunit;
namespace SqlToViz.Tests;
public class GoldenFuzz {
  [Fact] public void DifferentialFuzzVsPythonSdk() {
    var file = Environment.GetEnvironmentVariable("SQLTOVIZ_FUZZ");
    if (string.IsNullOrEmpty(file) || !File.Exists(file)) return;          // opt-in: CI sets SQLTOVIZ_FUZZ
    using var doc = JsonDocument.Parse(File.ReadAllText(file)); var root = doc.RootElement;
    double atol = root.GetProperty("atol").GetDouble(), rtol = root.GetProperty("rtol").GetDouble();
    var bad = new List<string>(); int ok = 0, rej = 0;
    foreach (var c in root.GetProperty("cases").EnumerateArray()) {
      var id = c.GetProperty("case_id").GetString()!; var exp = c.GetProperty("expected"); var sql = c.GetProperty("sql").GetString()!;
      Extracted? r = null; FeatureException? err = null;
      try { r = FeatureExtractor.Extract(sql, Golden.Schema(c), Golden.Rows(c)); } catch (FeatureException e) { err = e; } catch (Exception e) { bad.Add($"{id}: crash {e.GetType().Name} {e.Message}"); continue; }
      if (exp.TryGetProperty("rejected", out _)) { if (err is null) bad.Add($"{id}: expected rejection | {sql}"); else rej++; continue; }
      if (err is not null) { bad.Add($"{id}: unexpected rejection {err.Message} | {sql}"); continue; }
      var et = Golden.Doubles(exp.GetProperty("table_features"));
      for (int i = 0; i < 32; i++) if (!Golden.Close(r!.Table[i], et[i], atol, rtol)) bad.Add($"{id}: table[{i}] {r.Table[i]} vs {et[i]} | {sql}");
      var ec = exp.GetProperty("column_features").EnumerateArray().Select(Golden.Doubles).ToArray();
      for (int j = 0; j < ec.Length; j++) for (int i = 0; i < 28; i++) if (!Golden.Close(r!.Columns[j][i], ec[j][i], atol, rtol)) bad.Add($"{id}: col[{j}][{i}] {r.Columns[j][i]} vs {ec[j][i]} | {sql}");
      ok++;
    }
    Assert.Empty(bad.Take(8));
    Assert.True(ok > 0);
  }
}
