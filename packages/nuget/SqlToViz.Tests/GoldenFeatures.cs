using System.Security.Cryptography;
using System.Text.Json;
using SqlToViz;
using Xunit;
namespace SqlToViz.Tests;
public class GoldenFeatures {
  [Fact] public void ContractPinMatchesFrozenSpecBytes() {
    var sha = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(Golden.RepoFile("spec", "sqlvizspec-v1-features.json")))).ToLowerInvariant();
    Assert.Equal(sha, Contract.Sha256);
    using var g = Golden.Load(); Assert.Equal(sha, g.RootElement.GetProperty("contract_sha256").GetString());
  }
  [Fact] public void AllGoldenCasesFeaturesAndRejections() {
    using var g = Golden.Load(); var root = g.RootElement;
    double atol = root.GetProperty("atol").GetDouble(), rtol = root.GetProperty("rtol").GetDouble();
    int ok = 0, rej = 0; var bad = new List<string>();
    foreach (var c in root.GetProperty("cases").EnumerateArray()) {
      var id = c.GetProperty("case_id").GetString()!; var exp = c.GetProperty("expected");
      var sql = c.GetProperty("sql").GetString()!;
      if (exp.TryGetProperty("rejected", out _)) {
        try { FeatureExtractor.Extract(sql, Golden.Schema(c), Golden.Rows(c)); bad.Add(id + ": expected rejection"); }
        catch (FeatureException) { rej++; }
        continue;
      }
      Extracted r;
      try { r = FeatureExtractor.Extract(sql, Golden.Schema(c), Golden.Rows(c)); } catch (Exception e) { bad.Add(id + ": unexpected " + e.Message); continue; }
      var et = Golden.Doubles(exp.GetProperty("table_features"));
      for (int i = 0; i < 32; i++) if (!Golden.Close(r.Table[i], et[i], atol, rtol)) bad.Add($"{id}: table[{i}] {r.Table[i]} vs {et[i]}");
      var ec = exp.GetProperty("column_features").EnumerateArray().Select(Golden.Doubles).ToArray();
      if (r.Columns.Length != ec.Length) bad.Add(id + ": column count");
      else for (int j = 0; j < ec.Length; j++) for (int i = 0; i < 28; i++) if (!Golden.Close(r.Columns[j][i], ec[j][i], atol, rtol)) bad.Add($"{id}: col[{j}][{i}] {r.Columns[j][i]} vs {ec[j][i]}");
      ok++;
    }
    Assert.Empty(bad.Take(10));
    Assert.True(ok + rej >= 288); Assert.Equal(root.GetProperty("cases").GetArrayLength(), ok + rej);
  }
}
