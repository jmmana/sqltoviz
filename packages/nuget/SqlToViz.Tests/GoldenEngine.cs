using System.Text.Json;
using SqlToViz;
using SqlToViz.Onnx;
using Xunit;
namespace SqlToViz.Tests;
public class GoldenEngine {
  static readonly string Models = Path.Combine(Path.GetDirectoryName(typeof(OnnxEngine).Assembly.Location)!, "..", "..", "..", "..", "SqlToViz.Onnx", "models");
  [Fact] public void AllGoldenScoresClassesEligibilityAndRoles() {
    using var g = Golden.Load(); var root = g.RootElement;
    double atol = root.GetProperty("atol").GetDouble(), rtol = root.GetProperty("rtol").GetDouble();
    var engine = OnnxEngine.LoadDefault(); int n = 0; var bad = new List<string>();
    foreach (var c in root.GetProperty("cases").EnumerateArray()) {
      var exp = c.GetProperty("expected"); if (exp.TryGetProperty("rejected", out _)) continue;
      var id = c.GetProperty("case_id").GetString()!;
      var r = engine.Recommend(c.GetProperty("sql").GetString()!, Golden.Schema(c), Golden.Rows(c));
      var es = Golden.Doubles(exp.GetProperty("chart_scores"));
      for (int i = 0; i < 10; i++) if (!Golden.Close(r.Scores![Contract.BaseClasses[i]], es[i], atol, rtol)) bad.Add($"{id}: score {i}");
      if (r.BaseClass != exp.GetProperty("base_class").GetString() || r.FinalClass != exp.GetProperty("final_class").GetString() ||
          r.ConstraintChanged != exp.GetProperty("constraint_changed").GetBoolean() || r.RuleClass != exp.GetProperty("rule_class").GetString()) bad.Add($"{id}: class {r.BaseClass}/{r.FinalClass}");
      foreach (var p in exp.GetProperty("eligible").EnumerateObject()) if (r.Eligible[p.Name] != p.Value.GetBoolean()) bad.Add($"{id}: eligible {p.Name}");
      var roles = exp.GetProperty("roles").EnumerateArray().Select(v => v.GetString()).ToArray();
      if (!r.Roles!.Select(x => x.Role).SequenceEqual(roles!)) bad.Add($"{id}: roles");
      var rs = exp.GetProperty("role_scores").EnumerateArray().Select(Golden.Doubles).ToArray();
      for (int j = 0; j < rs.Length; j++) for (int i = 0; i < 5; i++) if (!Golden.Close(r.Roles![j].Scores[i], rs[j][i], atol, rtol)) bad.Add($"{id}: role score {j},{i}");
      n++;
    }
    Assert.Empty(bad.Take(10)); Assert.True(n >= 275);
  }
  [Fact] public void RulesAndConstraintsMatchGoldenWithoutModels() {
    using var g = Golden.Load();
    foreach (var c in g.RootElement.GetProperty("cases").EnumerateArray()) {
      var exp = c.GetProperty("expected"); if (exp.TryGetProperty("rejected", out _)) continue;
      var ex = FeatureExtractor.Extract(c.GetProperty("sql").GetString()!, Golden.Schema(c), Golden.Rows(c));
      Assert.Equal(exp.GetProperty("rule_class").GetString(), Rules.Predict(ex.Table, ex.Columns));
      var (cls, ch) = Rules.ConstrainedChoice(Golden.Doubles(exp.GetProperty("chart_scores")), ex.Table, ex.Columns);
      Assert.Equal(exp.GetProperty("final_class").GetString(), cls); Assert.Equal(exp.GetProperty("constraint_changed").GetBoolean(), ch);
    }
  }
  [Fact] public void ResultsAreExperimentalAndModelsReplaceable() {
    var r = OnnxEngine.LoadDefault().Recommend("SELECT a FROM t", new[] { new ColumnSpec("a") }, new[] { (IReadOnlyList<object?>)new object?[] { 1L } });
    Assert.Equal("experimental", r.ModelStatus); Assert.Contains(r.Warnings, w => w.Contains("not scientifically validated"));
    var dir = Directory.CreateTempSubdirectory().FullName; var man = JsonDocument.Parse(File.ReadAllText(Path.Combine(Models, "manifest.json"))).RootElement;
    foreach (var k in new[] { "chart", "role" }) File.Copy(Path.Combine(Models, man.GetProperty(k).GetProperty("file").GetString()!), Path.Combine(dir, "final_" + man.GetProperty(k).GetProperty("file").GetString()));
    File.WriteAllText(Path.Combine(dir, "manifest.json"), JsonSerializer.Serialize(new Dictionary<string, object> {
      ["chart"] = new { file = "final_" + man.GetProperty("chart").GetProperty("file").GetString(), sha256 = man.GetProperty("chart").GetProperty("sha256").GetString(), status = "validated" },
      ["role"] = new { file = "final_" + man.GetProperty("role").GetProperty("file").GetString(), sha256 = man.GetProperty("role").GetProperty("sha256").GetString(), status = "validated" } }));
    var r2 = OnnxEngine.LoadFromDirectory(dir).Recommend("SELECT a FROM t", new[] { new ColumnSpec("a") }, new[] { (IReadOnlyList<object?>)new object?[] { 1L } });
    Assert.Equal("validated", r2.ModelStatus); Assert.DoesNotContain(r2.Warnings, w => w.Contains("not scientifically validated"));
    Assert.Equal(typeof(Recommendation).GetProperties().Length, r2.GetType().GetProperties().Length);
  }
  [Fact] public void ChecksumAndSchemaEnforcedAndRulesOnlyEngine() {
    var chart = File.ReadAllBytes(Path.Combine(Models, "chart_model_candidate.onnx"));
    Assert.Throws<ModelException>(() => OnnxRunner.Create(chart, new string('0', 64), ModelKind.Chart));
    var sha = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(chart)).ToLowerInvariant();
    Assert.Throws<ModelException>(() => OnnxRunner.Create(chart, sha, ModelKind.Role));                 // chart model loaded as role model
    var r = new Engine().Recommend("SELECT SUM(x) AS s FROM t", new[] { new ColumnSpec("s") }, new[] { (IReadOnlyList<object?>)new object?[] { 3L } });
    Assert.Equal("kpi", r.FinalClass); Assert.Null(r.Scores); Assert.Null(r.Roles); Assert.Contains("rules-only", r.Warnings[0]);
  }
}
