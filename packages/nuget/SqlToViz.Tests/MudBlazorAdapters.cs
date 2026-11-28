using System.Text.Json;
using MudBlazor;
using SqlToViz;
using SqlToViz.MudBlazor;
using SqlToViz.Onnx;
using Xunit;
namespace SqlToViz.Tests;
public class MudBlazorAdapters {
  static IReadOnlyList<IReadOnlyDictionary<string, object?>> Rows(params (string c, double v)[] r) =>
    r.Select(t => (IReadOnlyDictionary<string, object?>)new Dictionary<string, object?> { ["cat"] = t.c, ["amt"] = t.v }).ToArray();
  [Fact] public void BarMapsToMudBarAndApexBar() {
    var rows = Rows(("a", 1), ("b", 2)); var plan = Preview.Recommend("SELECT cat, amt", rows);
    var m = Adapters.ToMudBlazor(plan, rows);
    Assert.Equal(AdapterKind.Bar, m.Kind); Assert.Equal(ChartType.Bar, m.ChartType);
    Assert.Equal(new[] { "a", "b" }, m.XAxisLabels); Assert.Equal(new[] { 1d, 2d }, m.Series[0].Data);
    var a = Adapters.ToApexConfig(plan, rows, "T");
    Assert.Equal(AdapterKind.Bar, a.Kind);
    foreach (var k in new[] { "chart", "plotOptions", "title", "xaxis", "yaxis", "dataLabels", "stroke", "legend", "tooltip", "noData", "series" }) Assert.True(a.Options.ContainsKey(k), k);
  }
  [Fact] public void HorizontalBarIsFlaggedInMudAndHorizontalInApex() {
    var rows = Enumerable.Range(0, 13).Select(i => Rows(($"c{i}", i))[0]).ToArray(); var plan = Preview.Recommend("SELECT cat, amt", rows);
    Assert.Equal("horizontal_bar", plan.ChartType);
    var m = Adapters.ToMudBlazor(plan, rows); Assert.True(m.HorizontalBar); Assert.Equal(ChartType.Bar, m.ChartType); Assert.NotEmpty(m.Notes);
    var po = (Dictionary<string, object?>)((Dictionary<string, object?>)Adapters.ToApexConfig(plan, rows).Options["plotOptions"]!)["bar"]!;
    Assert.Equal(true, po["horizontal"]);
  }
  [Fact] public void IsoDatesMapToLine() {
    var rows = Enumerable.Range(1, 5).Select(i => (IReadOnlyDictionary<string, object?>)new Dictionary<string, object?> { ["d"] = $"2024-01-0{i}", ["v"] = (double)i }).ToArray();
    var plan = Preview.Recommend("SELECT d, v", rows); Assert.Equal("line", plan.ChartType);
    Assert.Equal(ChartType.Line, Adapters.ToMudBlazor(plan, rows).ChartType);
    Assert.Equal(AdapterKind.Line, Adapters.ToApexConfig(plan, rows).Kind);
  }
  [Fact] public void KpiAndTableFallbacks() {
    var one = new[] { (IReadOnlyDictionary<string, object?>)new Dictionary<string, object?> { ["s"] = 42L } };
    var k = Adapters.ToMudBlazor(Preview.Recommend("SELECT SUM(x) AS s", one), one);
    Assert.Equal(AdapterKind.Kpi, k.Kind); Assert.Equal(42, k.Kpi!.Value);
    var multi = new[] { (IReadOnlyDictionary<string, object?>)new Dictionary<string, object?> { ["a"] = 1, ["b"] = 2, ["c"] = 3 } };
    var t = Adapters.ToMudBlazor(Preview.Recommend("SELECT * FROM t", multi), multi);
    Assert.Equal(AdapterKind.Table, t.Kind); Assert.Equal(new[] { "a", "b", "c" }, t.Table!.Columns); Assert.Equal("1", t.Table.Rows[0][0]);
    Assert.Equal(AdapterKind.Table, Adapters.ToApexConfig(new Plan("scatter", "a", "b", "x"), multi).Kind);
  }
  [Fact] public void MissingColumnsAndNullsDoNotThrow() {
    var rows = Rows(("a", 1)); Assert.Equal(AdapterKind.Table, Adapters.ToMudBlazor(new Plan("bar", "zzz", "amt", "x"), rows).Kind);
    var withNull = new[] { (IReadOnlyDictionary<string, object?>)new Dictionary<string, object?> { ["cat"] = "a", ["amt"] = null } };
    var m = Adapters.ToMudBlazor(new Plan("bar", "cat", "amt", "x"), withNull); Assert.Contains(m.Notes, n => n.Contains("NULL"));
    Assert.Equal(AdapterKind.Table, Adapters.ToMudBlazor(new Plan("bar", "cat", "amt", "x"), Array.Empty<IReadOnlyDictionary<string, object?>>()).Kind);
  }
  [Fact] public void GoldenFixturesProduceConsistentModels() {
    using var g = Golden.Load(); var engine = OnnxEngine.LoadDefault(); int charts = 0, kpis = 0, tables = 0, total = 0;
    foreach (var c in g.RootElement.GetProperty("cases").EnumerateArray()) {
      if (c.GetProperty("expected").TryGetProperty("rejected", out _)) continue;
      var schema = Golden.Schema(c); var rows = Golden.Rows(c);
      var rec = engine.Recommend(c.GetProperty("sql").GetString()!, schema, rows);
      var plan = Adapters.PlanFrom(rec, schema, rows); var dicts = Adapters.ToDicts(schema, rows);
      var m = Adapters.ToMudBlazor(plan, dicts); var a = Adapters.ToApexConfig(plan, dicts); total++;
      Assert.Equal(m.Kind, a.Kind);
      switch (m.Kind) {
        case AdapterKind.Bar or AdapterKind.HorizontalBar or AdapterKind.Line:
          charts++; Assert.Equal(rows.Count, m.XAxisLabels.Length); Assert.Equal(rows.Count, m.Series[0].Data.Length); Assert.Equal(rec.FinalClass == "line" ? ChartType.Line : ChartType.Bar, m.ChartType); break;
        case AdapterKind.Kpi: kpis++; Assert.Equal("kpi", rec.FinalClass); break;
        default: tables++; Assert.NotNull(m.Table); if (rows.Count > 0) Assert.Equal(schema.Select(s => s.Name).Distinct().Count(), m.Table!.Columns.Count); break;
      }
    }
    Assert.True(total >= 275); Assert.True(charts > 0 && kpis > 0 && tables > 0, $"charts={charts} kpis={kpis} tables={tables}");
  }
}
