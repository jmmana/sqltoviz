using System.Data;
using System.Globalization;
namespace SqlToViz;
public sealed record Plan(string ChartType,string? X,string? Y,string Reason,string Mode="deterministic-preview");
public static class Preview {
 internal static double? Number(object? v) {
  if(v is not (byte or sbyte or short or ushort or int or uint or long or ulong or float or double or decimal)) return null;
  double d=Convert.ToDouble(v,CultureInfo.InvariantCulture);return double.IsFinite(d)?d:null;
 }
 public static Plan Recommend(string sql,IReadOnlyList<IReadOnlyDictionary<string,object?>> rows) {
  if(string.IsNullOrWhiteSpace(sql)||sql.Length>20000||rows.Count<1||rows.Count>5000)throw new ArgumentException("Invalid SQL or row count");
  var keys=rows[0].Keys.ToArray();
  if(keys.Length<1||keys.Length>50||keys.Any(string.IsNullOrEmpty)||rows.Any(r=>r.Count!=keys.Length||keys.Any(k=>!r.ContainsKey(k)||r[k] is not (null or string or bool)&&Number(r[k]) is null)))throw new ArgumentException("Expected identical scalar columns");
  var nums=keys.Where(k=>rows.All(r=>Number(r[k]).HasValue)).ToArray();
  var cats=keys.Where(k=>rows.All(r=>r[k] is string s&&s.Length>0)).ToArray();
  if(rows.Count==1&&keys.Length==1&&nums.Length==1)return new("kpi",null,nums[0],"One numeric scalar");
  if(keys.Length==2&&nums.Length==1&&cats.Length==1&&rows.Count<=100){
   var labels=rows.Select(r=>(string)r[cats[0]]!).ToArray();
   if(labels.Distinct(StringComparer.Ordinal).Count()==labels.Length){
    bool temporal=labels.Length>=4&&labels.All(v=>DateOnly.TryParseExact(v,"yyyy-MM-dd",CultureInfo.InvariantCulture,DateTimeStyles.None,out _))&&labels.SequenceEqual(labels.OrderBy(v=>v,StringComparer.Ordinal));
    return new(temporal?"line":rows.Count>12?"horizontal_bar":"bar",cats[0],nums[0],temporal?"Ordered ISO dates":"Unique categories");
   }
  }
  return new("table",null,null,"No supported safe chart for shape");
 }
 public static Plan Recommend(string sql,DataTable table)=>Recommend(sql,table.Rows.Cast<DataRow>().Select(r=>(IReadOnlyDictionary<string,object?>)table.Columns.Cast<DataColumn>().ToDictionary(c=>c.ColumnName,c=>r.IsNull(c)?null:r[c])).ToArray());
 public static object ToApexCharts(Plan p,IReadOnlyList<IReadOnlyDictionary<string,object?>> rows){
  if(p.ChartType is not ("bar" or "horizontal_bar" or "line")||p.X is null||p.Y is null)throw new ArgumentException("Unsupported chart");
  return new { chart=new {type=p.ChartType=="line"?"line":"bar"},plotOptions=new {bar=new {horizontal=p.ChartType=="horizontal_bar"}},xaxis=new {categories=rows.Select(r=>r[p.X]).ToArray()},series=new[]{new{name=p.Y,data=rows.Select(r=>r[p.Y]).ToArray()}}};
 }
}
