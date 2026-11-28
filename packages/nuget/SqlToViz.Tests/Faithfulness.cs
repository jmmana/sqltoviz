// Replays parity/tools/gen_faithfulness.py cases (SQLTOVIZ_FAITH=<file>); errors measured against exact rational/decimal references.
using System.Text.Json;
using SqlToViz;
using Xunit;
namespace SqlToViz.Tests;
public class Faithfulness {
  static double? N(JsonElement e) => e.ValueKind == JsonValueKind.Null ? null : e.GetDouble();
  static double?[] Arr(JsonElement e) => e.EnumerateArray().Select(N).ToArray();
  static double Rel(double a, double b) => Math.Abs(a - b) / Math.Max(Math.Abs(b), 1e-300);
  [Fact] public void DetectorsMatchExactReferences() {
    var file = Environment.GetEnvironmentVariable("SQLTOVIZ_FAITH"); if (string.IsNullOrEmpty(file) || !File.Exists(file)) return;
    using var doc = JsonDocument.Parse(File.ReadAllText(file)); var root = doc.RootElement; var tol = root.GetProperty("tolerance");
    var worst = new Dictionary<string, double> { ["mad"] = 0, ["pearson"] = 0, ["temporal"] = 0, ["pareto"] = 0 };
    void Upd(string k, double v) => worst[k] = Math.Max(worst[k], v);
    foreach (var c in root.GetProperty("cases").EnumerateArray()) {
      var kind = c.GetProperty("kind").GetString()!; var e = c.GetProperty("expected");
      if (kind == "mad") {
        var r = Statistics.Mad(Arr(c.GetProperty("values"))); Assert.Equal(e.GetProperty("status").GetString(), r.Status);
        if (e.TryGetProperty("median", out var m)) { Upd("mad", m.GetDouble() != 0 ? Rel(r.Median!.Value, m.GetDouble()) : Math.Abs(r.Median!.Value)); var md = e.GetProperty("mad").GetDouble(); Upd("mad", md != 0 ? Rel(r.Mad!.Value, md) : Math.Abs(r.Mad!.Value)); }
        var eo = e.GetProperty("outliers").EnumerateArray().ToArray(); Assert.Equal(eo.Select(o => o.GetProperty("index").GetInt32()), r.Outliers.Select(o => o.Index));
        for (int i = 0; i < eo.Length; i++) Upd("mad", Rel(r.Outliers[i].Score, eo[i].GetProperty("score").GetDouble()));
      } else if (kind == "pearson") {
        var r = Statistics.Pearson(Arr(c.GetProperty("xs")), Arr(c.GetProperty("ys"))); Assert.Equal(e.GetProperty("status").GetString(), r.Status);
        if (e.GetProperty("status").GetString() == "ok") Upd("pearson", Math.Abs(r.R!.Value - e.GetProperty("r").GetDouble()));
      } else if (kind == "temporal") {
        var r = Statistics.Temporal(Arr(c.GetProperty("values"))); var ee = e.EnumerateArray().ToArray();
        Assert.Equal(ee.Select(x => x.GetProperty("status").GetString()), r.Select(x => x.Status));
        for (int i = 0; i < ee.Length; i++) {
          if (N(ee[i].GetProperty("delta")) is double d) Upd("temporal", d != 0 ? Rel(r[i].Delta!.Value, d) : Math.Abs(r[i].Delta!.Value));
          if (N(ee[i].GetProperty("relative_change")) is double rc) Upd("temporal", rc != 0 ? Rel(r[i].RelativeChange!.Value, rc) : Math.Abs(r[i].RelativeChange!.Value));
        }
      } else {
        var (status, items) = Statistics.Pareto(Arr(c.GetProperty("values")), c.GetProperty("coverage").GetDouble(), additive: true); Assert.Equal(e.GetProperty("status").GetString(), status);
        var ei = e.GetProperty("items").EnumerateArray().ToArray();
        Assert.Equal(ei.Select(x => x.GetProperty("index").GetInt32()), items.Select(x => x.Index)); Assert.Equal(ei.Select(x => x.GetProperty("included").GetBoolean()), items.Select(x => x.Included));
        for (int i = 0; i < ei.Length; i++) { Upd("pareto", Math.Abs(items[i].Share - ei[i].GetProperty("share").GetDouble())); Upd("pareto", Math.Abs(items[i].Cumulative - ei[i].GetProperty("cumulative").GetDouble())); }
      }
    }
    Console.WriteLine("dotnet worst errors " + JsonSerializer.Serialize(worst));
    Assert.True(Math.Max(worst["mad"], worst["temporal"]) < tol.GetProperty("relative").GetDouble() && worst["pearson"] < tol.GetProperty("pearson_abs").GetDouble() && worst["pareto"] < 1e-12, JsonSerializer.Serialize(worst));
  }
}
