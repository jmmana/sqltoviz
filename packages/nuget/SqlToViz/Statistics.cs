namespace SqlToViz;
public sealed record Outlier(int Index,double Score);
public sealed record MadResult(string Status,double? Median,double? Mad,IReadOnlyList<Outlier> Outliers);
public sealed record Shift(int Index,string Status,double? Delta,double? RelativeChange);
public sealed record ParetoItem(int Index,double Share,double Cumulative,bool Included);
public static class Statistics {
 static double Median(IEnumerable<double> xs){var a=xs.Order().ToArray();int i=a.Length/2;return a.Length%2==1?a[i]:a[i-1]/2+a[i]/2;}
 public static MadResult Mad(IEnumerable<double?> values,double threshold=3.5){
  if(!double.IsFinite(threshold)||threshold<=0)throw new ArgumentException("threshold");
  var p=values.Select((v,i)=>(v,i)).Where(t=>t.v.HasValue&&double.IsFinite(t.v.Value)).Select(t=>(v:t.v!.Value,t.i)).ToArray();
  if(p.Length<3)return new("insufficient_samples",null,null,[]);
  var m=Median(p.Select(t=>t.v));var mad=Median(p.Select(t=>Math.Abs(t.v-m)));
  if(mad==0)return new("zero_mad",m,0,[]);
  var z=p.Select(t=>new Outlier(t.i,.6744897501960817*((t.v-m)/mad))).ToArray();
  if(z.Any(t=>!double.IsFinite(t.Score)))return new("numeric_overflow",null,null,[]);
  return new("ok",m,mad,z.Where(t=>Math.Abs(t.Score)>threshold).ToArray());
 }
 public static IReadOnlyList<Shift> Temporal(IReadOnlyList<double?> values){
  var result=new List<Shift>();for(int i=1;i<values.Count;i++){
   var a=values[i-1];var b=values[i];if(!a.HasValue||!b.HasValue||!double.IsFinite(a.Value)||!double.IsFinite(b.Value)){result.Add(new(i,"missing",null,null));continue;}
   var d=b.Value-a.Value;if(!double.IsFinite(d)){result.Add(new(i,"numeric_overflow",null,null));continue;}
   if(a==0){result.Add(new(i,"zero_baseline",d,null));continue;}
   var c=d/Math.Abs(a.Value);result.Add(double.IsFinite(c)?new(i,"ok",d,c):new(i,"numeric_overflow",d,null));
  }return result;
 }
 public static (string Status,IReadOnlyList<ParetoItem> Items) Pareto(IReadOnlyList<double?> values,double coverage=.8,bool additive=false){
  if(!double.IsFinite(coverage)||coverage<=0||coverage>1)throw new ArgumentException("coverage");
  if(!additive)return ("unknown_additivity",[]);
  if(values.Any(v=>!v.HasValue||!double.IsFinite(v.Value)||v.Value<0))return ("invalid_weights",[]);
  var scale=values.Select(v=>v!.Value).DefaultIfEmpty(0).Max();if(scale==0)return ("zero_total",[]);
  var total=values.Sum(v=>v!.Value/scale);var running=0d;bool reached=false;var items=new List<ParetoItem>();
  foreach(var t in values.Select((v,i)=>(v:v!.Value,i)).OrderByDescending(t=>t.v).ThenBy(t=>t.i)){var share=t.v/scale/total;running=Math.Min(1,running+share);items.Add(new(t.i,share,running,!reached&&t.v>0));reached|=running>=coverage-1e-15;}
  return ("ok",items);
 }
 public static (string Status,int N,double? R) Pearson(IReadOnlyList<double?> xs,IReadOnlyList<double?> ys){
  if(xs.Count!=ys.Count)throw new ArgumentException("paired arrays");
  var p=xs.Zip(ys).Where(t=>t.First.HasValue&&t.Second.HasValue&&double.IsFinite(t.First.Value)&&double.IsFinite(t.Second.Value)).Select(t=>(x:t.First!.Value,y:t.Second!.Value)).ToArray();
  int n=p.Length;if(n<3)return ("insufficient_samples",n,null);
  var sx=p.Max(t=>Math.Abs(t.x));var sy=p.Max(t=>Math.Abs(t.y));if(sx==0||sy==0)return ("constant_column",n,null);
  var a=p.Select(t=>t.x/sx).ToArray();var b=p.Select(t=>t.y/sy).ToArray();var ma=a.Average();var mb=b.Average();
  double aa=0,bb=0,ab=0;for(int i=0;i<n;i++){var x=a[i]-ma;var y=b[i]-mb;aa+=x*x;bb+=y*y;ab+=x*y;}
  if(aa==0||bb==0)return ("constant_column",n,null);return ("ok",n,Math.Clamp(ab/Math.Sqrt(aa*bb),-1,1));
 }
}
