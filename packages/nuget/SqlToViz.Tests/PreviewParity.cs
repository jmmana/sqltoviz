using System.Text.Json;
using SqlToViz;
using Xunit;
public class PreviewParity {
 static JsonDocument Load(){
  var d=new DirectoryInfo(AppContext.BaseDirectory);
  while(d!=null){var path=Path.Combine(d.FullName,"parity","preview-v0.1.json");if(File.Exists(path))return JsonDocument.Parse(File.ReadAllText(path));d=d.Parent;}
  throw new FileNotFoundException("preview parity fixtures");
 }
 static object? Cell(JsonElement e)=>e.ValueKind switch{JsonValueKind.Null=>null,JsonValueKind.String=>e.GetString(),JsonValueKind.Number=>e.GetDouble(),JsonValueKind.True=>true,JsonValueKind.False=>false,_=>throw new ArgumentException("scalar")};
 static string? Opt(JsonElement e,string name)=>e.TryGetProperty(name,out var v)?v.GetString():null;
 static double?[] Numbers(JsonElement e)=>e.EnumerateArray().Select(v=>v.ValueKind==JsonValueKind.Null?(double?)null:v.GetDouble()).ToArray();
 static int[] Indices(JsonElement e)=>e.EnumerateArray().Select(v=>v.GetInt32()).ToArray();
 [Fact] public void Charts(){using var doc=Load();foreach(var c in doc.RootElement.GetProperty("charts").EnumerateArray()){
  var rows=c.GetProperty("rows").EnumerateArray().Select(r=>(IReadOnlyDictionary<string,object?>)r.EnumerateObject().ToDictionary(p=>p.Name,p=>Cell(p.Value))).ToArray();
  var p=Preview.Recommend(c.GetProperty("sql").GetString()!,rows);
  Assert.Equal(c.GetProperty("chart").GetString(),p.ChartType);Assert.Equal(Opt(c,"x"),p.X);Assert.Equal(Opt(c,"y"),p.Y);
 }}
 [Fact] public void Detectors(){using var doc=Load();var s=doc.RootElement.GetProperty("statistics");
 foreach(var c in s.GetProperty("mad").EnumerateArray()){var p=Statistics.Mad(Numbers(c.GetProperty("values")));Assert.Equal(c.GetProperty("status").GetString(),p.Status);Assert.Equal(Indices(c.GetProperty("indices")),p.Outliers.Select(v=>v.Index).ToArray());}
 foreach(var c in s.GetProperty("temporal").EnumerateArray()){var p=Statistics.Temporal(Numbers(c.GetProperty("values")));Assert.Equal(c.GetProperty("statuses").EnumerateArray().Select(v=>v.GetString()).ToArray(),p.Select(v=>v.Status).ToArray());Assert.Equal(Numbers(c.GetProperty("changes")),p.Select(v=>v.RelativeChange).ToArray());}
 foreach(var c in s.GetProperty("pareto").EnumerateArray()){var p=Statistics.Pareto(Numbers(c.GetProperty("values")),additive:c.GetProperty("additive").GetBoolean());Assert.Equal(c.GetProperty("status").GetString(),p.Status);Assert.Equal(Indices(c.GetProperty("indices")),p.Items.Where(v=>v.Included).Select(v=>v.Index).ToArray());}
 foreach(var c in s.GetProperty("pearson").EnumerateArray()){var p=Statistics.Pearson(Numbers(c.GetProperty("xs")),Numbers(c.GetProperty("ys")));Assert.Equal(c.GetProperty("status").GetString(),p.Status);var v=c.GetProperty("r");if(v.ValueKind==JsonValueKind.Null)Assert.Null(p.R);else Assert.InRange(Math.Abs(p.R!.Value-v.GetDouble()),0,doc.RootElement.GetProperty("tolerance").GetDouble());}
 }}
}
