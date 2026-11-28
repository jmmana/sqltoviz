// SqlVizSpec-Outputs-v1.0.0 (additive extension): specialise a base chart class into one of 21 concrete outputs.
// Port of packages/python/sqltoviz/outputs.py; behaviour is pinned by parity/outputs_v1.json. Thresholds are design choices, not validated findings.
using System.Globalization;
using System.Text.Json;
namespace SqlToViz;

public sealed record OutputRejection(string Output, string ReasonCode);
/// <summary>Result of <see cref="Outputs.SpecializeOutputs"/>. Encoding/param values are string, null, double, int, or lists/dictionaries of those.</summary>
public sealed record OutputResult(string Output, IReadOnlyDictionary<string, object?> Encodings, IReadOnlyDictionary<string, object?> Params,
  IReadOnlyList<OutputRejection> Rejected, IReadOnlyList<string> FallbackChain);

public static class Outputs {
  sealed record Pre(string Id, string Reason);
  static readonly Dictionary<string, string[]> Specialization = new();
  static readonly Dictionary<string, Pre[]> Definitions = new();
  static readonly Dictionary<string, string> Aliases = new();
  static readonly int MaxCat, MinHist, MinViolin, MinBox, MinRowsLine, MinPairs, HeatCap, LeafCap, DonutLo, DonutHi;
  static readonly double IqrFactor;

  static Outputs() {
    using var doc = JsonDocument.Parse(OutputsContract.Json);
    var r = doc.RootElement;
    foreach (var p in r.GetProperty("specialization").EnumerateObject()) Specialization[p.Name] = p.Value.EnumerateArray().Select(e => e.GetString()!).ToArray();
    foreach (var p in r.GetProperty("outputs_definition").EnumerateObject())
      Definitions[p.Name] = p.Value.GetProperty("preconditions").EnumerateArray().Select(e => new Pre(e.GetProperty("id").GetString()!, e.GetProperty("reason").GetString()!)).ToArray();
    foreach (var p in r.GetProperty("aliases").EnumerateObject()) Aliases[p.Name] = p.Value.GetString()!;
    var t = r.GetProperty("thresholds");
    MaxCat = t.GetProperty("max_categories_bar").GetInt32(); MinHist = t.GetProperty("min_samples_histogram").GetInt32(); MinViolin = t.GetProperty("min_samples_violin").GetInt32();
    MinBox = t.GetProperty("min_group_boxplot").GetInt32(); MinRowsLine = t.GetProperty("min_rows_line").GetInt32(); MinPairs = t.GetProperty("min_pairs_scatter").GetInt32();
    HeatCap = t.GetProperty("heatmap_max_categories").GetInt32(); LeafCap = t.GetProperty("treemap_max_leaves").GetInt32();
    DonutLo = t.GetProperty("donut_slices")[0].GetInt32(); DonutHi = t.GetProperty("donut_slices")[1].GetInt32();
    IqrFactor = t.GetProperty("boxplot_iqr_factor").GetDouble();
  }

  /// <summary>Map legacy aliases (kpi_card) to the canonical output name.</summary>
  public static string NormalizeOutput(string name) => Aliases.TryGetValue(name, out var v) ? v : name;

  // ------------------------------------------------------------------ helpers over loosely typed metadata
  static IReadOnlyDictionary<string, object?>? Dict(object? o) => o as IReadOnlyDictionary<string, object?>;
  static object? Get(IReadOnlyDictionary<string, object?>? d, string k) => d is not null && d.TryGetValue(k, out var v) ? v : null;
  static bool Has(IReadOnlyDictionary<string, object?>? d, string k) => d is not null && d.ContainsKey(k);
  static IReadOnlyList<object?>? List(object? o) => o is string ? null : o as IReadOnlyList<object?>;
  static bool IsNumber(object? x) => x is not null && x is not bool && FeatureExtractor.IsNumericType(x) && double.IsFinite(FeatureExtractor.ToDouble(x));
  static double D(object? x) => x is null ? double.NaN : x is bool b ? (b ? 1 : 0) : x is string ? double.NaN : FeatureExtractor.ToDouble(x);
  static bool Missing(object? v) => FeatureExtractor.IsMissing(v);
  static string R(double d) => (d == 0 ? 0.0 : d).ToString("R", CultureInfo.InvariantCulture);
  // equality key mirroring Python hashing/equality of JSON scalars (1 == 1.0 == True)
  static string Key(object? v) => v is null ? "N" : v is string s ? "s:" + s : "d:" + R(D(v));

  static string PyStr(object v) {
    if (v is string s) return s;
    if (v is bool b) return b ? "True" : "False";
    if (v is double or float or decimal) {
      double d = D(v);
      if (double.IsNaN(d)) return "nan";
      if (double.IsInfinity(d)) return d > 0 ? "inf" : "-inf";
      if (d == 0) return 1 / d < 0 ? "-0.0" : "0.0";
      var e = d.ToString("E16", CultureInfo.InvariantCulture);
      var sh = d.ToString("R", CultureInfo.InvariantCulture);
      // extract shortest digits and decimal exponent from the round-trip string
      bool neg = sh[0] == '-'; if (neg) sh = sh[1..];
      int exp = 0; var mant = sh; int ei = sh.IndexOfAny(new[] { 'E', 'e' });
      if (ei >= 0) { exp = int.Parse(sh[(ei + 1)..], CultureInfo.InvariantCulture); mant = sh[..ei]; }
      int dot = mant.IndexOf('.'); string digits = mant.Replace(".", ""); int point = (dot < 0 ? mant.Length : dot) + exp;
      int lead = 0; while (lead < digits.Length - 1 && digits[lead] == '0') { lead++; } digits = digits[lead..]; point -= lead;
      digits = digits.TrimEnd('0'); if (digits.Length == 0) digits = "0";
      int dexp = point - 1; string res;
      if (dexp < -4 || dexp >= 16) res = digits[0] + (digits.Length > 1 ? "." + digits[1..] : "") + "e" + (dexp < 0 ? "-" : "+") + Math.Abs(dexp).ToString("00", CultureInfo.InvariantCulture);
      else if (point <= 0) res = "0." + new string('0', -point) + digits;
      else if (point >= digits.Length) res = digits + new string('0', point - digits.Length) + ".0";
      else res = digits[..point] + "." + digits[point..];
      _ = e; return (neg ? "-" : "") + res;
    }
    return Convert.ToString(v, CultureInfo.InvariantCulture) ?? "";
  }

  static double SumL(IEnumerable<double> xs) { double a = 0.0; foreach (var v in xs) a += v; return a; }
  static double Q7(List<double> x, double p) {
    int n = x.Count; double h = (n - 1) * p; int lo = (int)Math.Floor(h), hi = Math.Min(lo + 1, n - 1);
    return x[lo] + (h - lo) * (x[hi] - x[lo]);
  }
  static double Sd(List<double> x) { double m = SumL(x) / x.Count; return Math.Sqrt(SumL(x.Select(v => (v - m) * (v - m))) / (x.Count - 1)); }

  sealed class Col { public string Name = ""; public string Type = ""; }

  sealed class Ctx {
    public List<Col> Cols = new(); public IReadOnlyList<IReadOnlyList<object?>> Rows = Array.Empty<IReadOnlyList<object?>>(); public int N;
    public IReadOnlyDictionary<string, object?>? Meta; public IReadOnlyDictionary<string, string>? Roles; public IReadOnlyDictionary<string, bool> El = new Dictionary<string, bool>();
    public Dictionary<string, int> Idx = new();
    public Dictionary<string, object?> Enc = new(); public Dictionary<string, object?> Params = new();
    public List<string> Used = new(), Dims = new(); public string? Sample, Group, Output; public string[] Carriers = Array.Empty<string>();
    public void Reset() { Enc = new(); Params = new(); Used = new(); Dims = new(); Sample = null; Group = null; Output = null; Carriers = Array.Empty<string>(); }
    public List<object?> Vals(string name) { int j = Idx[name]; return Rows.Select(r => r[j]).ToList(); }
    public string TypeOf(string n) => Cols[Idx[n]].Type;
    string? Role(string n) => Roles is not null && Roles.TryGetValue(n, out var r) ? r : null;
    public List<string> OfType(string t, string? role = null, params string[] exclude) {
      var c = Cols.Where(x => x.Type == t && !exclude.Contains(x.Name) && Role(x.Name) != "ignore_tooltip").Select(x => x.Name).ToList();
      if (role is not null) { var pref = c.Where(n => Role(n) == role).ToList(); c = pref.Concat(c.Where(n => !pref.Contains(n))).ToList(); }
      return c;
    }
    public IReadOnlyDictionary<string, object?>? ColMeta(string? name) { var m = Dict(Get(Meta, "columns")); return name is null ? null : Dict(Get(m, name)); }
    public object? CM(string? name, string key) => Get(ColMeta(name), key);
    public bool Flag(string key) => Get(Meta, key) is true;
    public string EncS(string k) => (string)Enc[k]!;
    public int UniqueCount(List<string> names) {
      if (names.Count == 0) return 0;
      var cols = names.Select(n => Vals(n)).ToList(); var set = new HashSet<string>(StringComparer.Ordinal);
      for (int i = 0; i < N; i++) set.Add(string.Join("\u0001", names.Select((n, k) => KeyK(n, cols[k][i]))));
      return set.Count;
    }
    string KeyK(string n, object? v) {
      if (TypeOf(n) == "temporal") { var t = FeatureExtractor.ParseTemporal(v); return t is null ? "N" : "d:" + R(t.Value); }
      return IsNumber(v) ? "d:" + R(D(v)) : Key(v);
    }
    public int Distinct(string n) => Vals(n).Select(Key).Distinct(StringComparer.Ordinal).Count();
  }

  // ------------------------------------------------------------------ shape checks
  static bool ShapeCat(Ctx c) {
    var n = c.OfType("nominal", "x_axis"); var q = c.OfType("quantitative", "y_axis");
    if (n.Count == 0 || q.Count == 0) return false;
    c.Enc = new() { ["category"] = n[0], ["value"] = q[0] }; c.Dims = new() { n[0] }; c.Used = new() { n[0], q[0] }; return true;
  }
  static bool ShapeTwo(Ctx c) {
    var n = c.OfType("nominal", "x_axis"); var q = c.OfType("quantitative", "y_axis");
    if (n.Count < 2 || q.Count == 0) return false;
    var cat = n[0]; var ser = c.OfType("nominal", "color_series", cat)[0];
    c.Enc = c.Output == "heatmap" ? new() { ["row"] = cat, ["column"] = ser, ["value"] = q[0] } : new() { ["category"] = cat, ["series"] = ser, ["value"] = q[0] };
    c.Dims = new() { cat, ser }; c.Used = new() { cat, ser, q[0] }; return true;
  }
  static bool ShapeTime(Ctx c, int wantQ) {
    var t = c.OfType("temporal", "x_axis"); var q = c.OfType("quantitative", "y_axis");
    if (t.Count == 0 || q.Count < wantQ) return false;
    if (wantQ == 2) return ShapeDual(c, t[0]);
    c.Enc = new() { ["x"] = t[0], ["y"] = q[0] }; c.Dims = new() { t[0] }; c.Used = new() { t[0], q[0] }; return true;
  }
  static bool ShapeDual(Ctx c, string t) {
    c.Enc = new() { ["x"] = t }; c.Dims = new() { t };
    var q = c.OfType("quantitative");
    var left = q.Where(n => Get(c.ColMeta(n), "axis") is "left").ToList(); var right = q.Where(n => Get(c.ColMeta(n), "axis") is "right").ToList();
    if (left.Count > 0 && right.Count > 0) { c.Enc["y_left"] = left[0]; c.Enc["y_right"] = right[0]; } else { c.Enc["y_left"] = q[0]; c.Enc["y_right"] = q[1]; }
    c.Used = new() { t, c.EncS("y_left"), c.EncS("y_right") }; return true;
  }
  static bool Series(Ctx c) {
    var t = c.OfType("temporal", "x_axis"); var n = c.OfType("nominal", "color_series"); var q = c.OfType("quantitative", "y_axis");
    if (t.Count == 0 || n.Count == 0 || q.Count == 0) return false;
    c.Enc = new() { ["x"] = t[0], ["series"] = n[0], ["y"] = q[0] }; c.Dims = new() { t[0], n[0] }; c.Used = new() { t[0], n[0], q[0] }; return true;
  }
  static bool Scatter(Ctx c) {
    var q = c.OfType("quantitative", "x_axis"); if (q.Count < 2) return false;
    c.Enc = new() { ["x"] = q[0], ["y"] = q[1] }; c.Used = q.Take(2).ToList(); return true;
  }
  static bool Bubble(Ctx c) {
    var q = c.OfType("quantitative", "x_axis"); if (q.Count < 3) return false;
    var sz = q.Where(n => c.Roles is not null && c.Roles.TryGetValue(n, out var r) && r == "size_or_secondary").ToList();
    var size = sz.Count > 0 ? sz[0] : q[2]; var xy = q.Where(n => n != size).Take(2).ToList();
    c.Enc = new() { ["x"] = xy[0], ["y"] = xy[1], ["size"] = size }; c.Used = new() { xy[0], xy[1], size }; return true;
  }

  // ------------------------------------------------------------------ value checks
  static bool NoMissing(Ctx c) => !c.Used.Any(n => c.Vals(n).Any(Missing));
  static bool UniqueDims(Ctx c) => c.UniqueCount(c.Dims) == c.N;
  static bool Cap(Ctx c) => c.Dims.Where(n => c.TypeOf(n) == "nominal").All(n => c.Distinct(n) <= MaxCat);
  static string? MeasureKey(Ctx c) => (c.Enc.TryGetValue("value", out var v) && v is string s && s.Length > 0) ? s : (c.Enc.TryGetValue("y", out var y) ? y as string : null);
  static bool Additive(Ctx c) => c.CM(MeasureKey(c), "additive") is true;
  static bool NonNeg(Ctx c) => c.Vals(MeasureKey(c)!).All(v => D(v) >= 0);
  static bool Grid(Ctx c) {
    var a = c.Dims[0]; var b = c.Dims[1];
    return (long)c.Distinct(a) * c.Distinct(b) == c.N || Get(c.Meta, "missing_cells") is "zero" or "blank";
  }
  static bool ValuePresent(Ctx c) {
    var q = c.OfType("quantitative", "y_axis"); if (q.Count == 0) return false;
    c.Enc["value"] = q[0]; return !Missing(c.Vals(q[0])[0]);
  }
  static bool Goal(Ctx c) {
    var g = Dict(Get(c.Meta, "goal")); if (g is null) return false;
    if (IsNumber(Get(g, "value")) && !Has(g, "column")) { c.Params["goal"] = D(g["value"]); c.Enc["goal"] = null; return true; }
    if (Get(g, "column") is string col && !Has(g, "value") && c.Idx.ContainsKey(col) && c.TypeOf(col) == "quantitative" && c.N == 1 && IsNumber(c.Vals(col)[0])) {
      c.Params["goal"] = D(c.Vals(col)[0]); c.Enc["goal"] = col; return true;
    }
    return false;
  }
  static bool GoalBounds(Ctx c) {
    var b = List(Get(Dict(c.Meta!["goal"]), "bounds"));
    if (!(b is not null && b.Count == 2 && b.All(IsNumber) && D(b[0]) < D(b[1]))) return false;
    c.Enc["min"] = null; c.Enc["max"] = null; c.Params["min"] = D(b[0]); c.Params["max"] = D(b[1]);
    return D(b[0]) <= (double)c.Params["goal"]! && (double)c.Params["goal"]! <= D(b[1]);
  }
  static bool InBounds(Ctx c) { double v = D(c.Vals(c.EncS("value"))[0]); return (double)c.Params["min"]! <= v && v <= (double)c.Params["max"]!; }
  static bool WfOrder(Ctx c) {
    var o = Get(Dict(Get(c.Meta, "waterfall")), "order_by") as string;
    if (o is null || !c.Idx.ContainsKey(o)) return false;
    var v = c.Vals(o);
    if (v.Any(Missing) || v.Select(RepKey).Distinct(StringComparer.Ordinal).Count() != v.Count) return false;
    c.Enc["order_by"] = o; return true;
  }
  // Python repr()-level identity (1 and 1.0 differ)
  static string RepKey(object? x) => x switch { null => "N", string s => "s:" + s, bool b => "b:" + b, double or float or decimal => "f:" + R(D(x)), _ => "i:" + Convert.ToString(x, CultureInfo.InvariantCulture) };
  static bool WfTotal(Ctx c) {
    var t = Get(Dict(c.Meta!["waterfall"]), "total"); if (!IsNumber(t)) return false;
    c.Params["total"] = D(t); return true;
  }
  static bool Reconciles(Ctx c) {
    double s = SumL(c.Vals(c.EncS("value")).Select(D)), t = (double)c.Params["total"]!;
    c.Params["sum"] = s; c.Params["diff"] = s - t;
    return Math.Abs(s - t) <= 1e-6 + 1e-6 * Math.Abs(t);
  }
  static bool SliceRange(Ctx c) => DonutLo <= c.N && c.N <= DonutHi;
  static bool PosTotal(Ctx c) { double t = SumL(c.Vals(c.EncS("value")).Select(D)); c.Params["total"] = t; return t > 0; }
  static bool Hier(Ctx c, int depth) {
    var lv = List(Get(Dict(Get(c.Meta, "hierarchy")), "levels"));
    if (!(lv is not null && lv.Count >= depth && lv.All(x => x is string s && c.Idx.ContainsKey(s) && c.TypeOf(s) == "nominal") && lv.Distinct().Count() == lv.Count)) return false;
    var names = lv.Select(x => (string)x!).ToList(); c.Dims = names; c.Enc["levels"] = names.ToList(); return true;
  }
  static bool Weight(Ctx c) {
    var w = Get(Dict(c.Meta!["hierarchy"]), "weight") as string;
    if (!(w is not null && c.Idx.ContainsKey(w) && c.TypeOf(w) == "quantitative")) return false;
    c.Enc["weight"] = w; c.Used = c.Dims.Concat(new[] { w }).ToList(); return true;
  }

  // ------------------------------------------------------------------ raw-sample checks
  static bool RawDeclared(Ctx c) { var r = Get(c.Meta, "raw_samples"); return r is true || Dict(r) is not null; }
  static bool SampleCol(Ctx c) {
    var r = Dict(Get(c.Meta, "raw_samples")); var q = c.OfType("quantitative", "y_axis");
    var colo = Get(r, "column"); string col;
    if (colo is null) { if (q.Count != 1) return false; col = q[0]; }
    else if (colo is string cs && q.Contains(cs)) col = cs;
    else return false;
    var go = Get(r, "group"); string? g = null;
    if (go is not null) { if (!(go is string gs && c.Idx.ContainsKey(gs) && gs != col && c.TypeOf(gs) == "nominal")) return false; g = (string)go; }
    if (c.Output == "histogram") g = null;
    c.Sample = col; c.Group = g;
    c.Enc = c.Output == "histogram" ? new() { ["value"] = col } : new() { ["value"] = col, ["group"] = g };
    return true;
  }
  static bool PrecomputedOk(Ctx c) {
    var r = Dict(Get(c.Meta, "raw_samples")); var q = c.OfType("quantitative", "y_axis");
    var colo = Get(r, "column"); string? col = colo is string s && s.Length > 0 ? s : (q.Count > 0 ? q[0] : null);
    if (colo is not null && colo is not string) col = null;
    return col is null || !(c.CM(col, "kind") is "bin" or "quantile");
  }
  // {group key: sorted finite samples}; rows with a missing measure are dropped; None key sorts as ""
  static List<(string? Key, List<double> X)> Groups(Ctx c) {
    var vs = c.Vals(c.Sample!); var gs = c.Group is not null ? c.Vals(c.Group) : null;
    var order = new List<string?>(); var map = new Dictionary<string, List<double>>(StringComparer.Ordinal); List<double>? nullList = null;
    for (int i = 0; i < vs.Count; i++) {
      if (Missing(vs[i])) continue;
      var g = gs?[i]; double v = D(vs[i]); if (v == 0) v = 0.0;
      if (g is null) { if (nullList is null) { nullList = new(); order.Add(null); } nullList.Add(v); }
      else { var k = PyStr(g); if (!map.TryGetValue(k, out var l)) { l = new(); map[k] = l; order.Add(k); } l.Add(v); }
    }
    return order.Select(k => (Key: k, X: (k is null ? nullList! : map[k]).OrderBy(v => v).ToList())).OrderBy(e => e.Key ?? "", StringComparer.Ordinal).ToList();
  }
  static bool GroupDeclared(Ctx c) => c.Group is not null;
  static bool TwoGroups(Ctx c) => Groups(c).Count >= 2;
  static bool GroupComplete(Ctx c) => c.Group is null || !c.Vals(c.Group).Any(Missing);
  static bool GroupCap(Ctx c) => Groups(c).Count <= MaxCat;
  static bool MinHistC(Ctx c) {
    var x = Groups(c).FirstOrDefault(e => e.Key is null).X ?? new List<double>();
    if (x.Count < MinHist) return false;
    int k = (x.Count <= 1 ? 0 : 64 - System.Numerics.BitOperations.LeadingZeroCount((ulong)(x.Count - 1))) + 1;
    c.Params["n"] = x.Count; c.Params["bins"] = k; c.Params["min"] = x[0]; c.Params["max"] = x[^1]; c.Params["width"] = (x[^1] - x[0]) / k; return true;
  }
  static bool MinViolinC(Ctx c) { var g = Groups(c); return g.Count > 0 && g.All(e => e.X.Count >= MinViolin); }
  static bool NonConst(Ctx c) {
    var g = Groups(c);
    if (!g.All(e => e.X[0] != e.X[^1])) return false;
    if (c.Output == "violin") {
      var gl = new List<Dictionary<string, object?>>();
      foreach (var (k, x) in g) {
        double sd = Sd(x), iqr = Q7(x, 0.75) - Q7(x, 0.25), s = iqr > 0 ? Math.Min(sd, iqr / 1.34) : sd;
        gl.Add(new() { ["group"] = k, ["n"] = x.Count, ["bandwidth"] = 0.9 * s * Math.Pow(x.Count, -0.2) });
      }
      c.Params["groups"] = gl;
    }
    return true;
  }
  static bool MinBoxC(Ctx c) {
    var g = Groups(c);
    if (g.Count == 0 || !g.All(e => e.X.Count >= MinBox)) return false;
    var gl = new List<Dictionary<string, object?>>();
    foreach (var (k, x) in g) {
      double q1 = Q7(x, 0.25), med = Q7(x, 0.5), q3 = Q7(x, 0.75), i = IqrFactor * (q3 - q1);
      var inside = x.Where(v => q1 - i <= v && v <= q3 + i).ToList();
      gl.Add(new() { ["group"] = k, ["n"] = x.Count, ["q1"] = q1, ["median"] = med, ["q3"] = q3, ["whisker_low"] = inside[0], ["whisker_high"] = inside[^1], ["outliers"] = x.Count - inside.Count });
    }
    c.Params["groups"] = gl; return true;
  }

  // ------------------------------------------------------------------ dual axis, scatter, misc
  static readonly string[] Ys = { "y_left", "y_right" };
  static bool DualDeclared(Ctx c) => Dict(Get(c.Meta, "columns")) is { } m && Ys.All(k => Dict(Get(m, c.EncS(k))) is not null);
  static bool Units(Ctx c) => Ys.All(k => c.CM(c.EncS(k), "unit") is string { Length: > 0 });
  static bool AxisLabels(Ctx c) => Ys.All(k => c.CM(c.EncS(k), "label") is string { Length: > 0 });
  static bool AxesDistinct(Ctx c) => c.CM(c.EncS("y_left"), "axis") is "left" && c.CM(c.EncS("y_right"), "axis") is "right";
  static bool MeasuresDistinct(Ctx c) {
    if (c.EncS("y_left") == c.EncS("y_right")) return false;
    var a = c.Vals(c.EncS("y_left")).Select(Key).ToList(); var b = c.Vals(c.EncS("y_right")).Select(Key).ToList();
    return !a.SequenceEqual(b, StringComparer.Ordinal);
  }
  static bool SizeUnit(Ctx c) => c.CM(c.EncS("size"), "unit") is string { Length: > 0 };

  static readonly Dictionary<string, Func<Ctx, bool>> Checks = new() {
    ["base_eligible"] = c => c.Carriers.Any(b => c.El.TryGetValue(b, out var v) && v),
    ["single_row"] = c => c.N == 1, ["value_present"] = ValuePresent,
    ["goal_declared"] = Goal, ["goal_bounds_valid"] = GoalBounds, ["value_within_bounds"] = InBounds,
    ["cat_measure_shape"] = ShapeCat, ["two_dim_shape"] = ShapeTwo, ["time_shape"] = c => ShapeTime(c, 1), ["series_shape"] = Series,
    ["scatter_shape"] = Scatter, ["bubble_shape"] = Bubble,
    ["no_missing_used"] = NoMissing, ["unique_categories"] = UniqueDims, ["unique_pairs"] = UniqueDims, ["unique_time"] = UniqueDims, ["unique_paths"] = UniqueDims, ["category_cap"] = Cap,
    ["measure_additive"] = Additive, ["nonnegative"] = NonNeg, ["groups_disjoint"] = c => c.Flag("groups_disjoint"),
    ["groups_exhaustive"] = c => c.Flag("groups_exhaustive"), ["grid_or_missing_cells_declared"] = Grid,
    ["order_declared"] = WfOrder, ["total_declared"] = WfTotal, ["reconciles"] = Reconciles,
    ["slice_range"] = SliceRange, ["positive_total"] = PosTotal,
    ["hierarchy_declared"] = c => Hier(c, 1), ["hierarchy_depth_two"] = c => Hier(c, 2), ["weight_declared"] = Weight,
    ["weight_additive"] = c => c.CM(c.EncS("weight"), "additive") is true,
    ["weight_positive"] = c => c.Vals(c.EncS("weight")).All(v => D(v) > 0), ["leaf_cap"] = c => c.N <= LeafCap,
    ["raw_samples_declared"] = RawDeclared, ["not_precomputed"] = PrecomputedOk, ["sample_column_resolved"] = SampleCol,
    ["group_declared"] = GroupDeclared, ["groups_min_two"] = TwoGroups, ["group_complete"] = GroupComplete, ["group_cap"] = GroupCap, ["min_samples_histogram"] = MinHistC, ["min_samples_violin"] = MinViolinC,
    ["min_group_boxplot"] = MinBoxC, ["non_constant"] = NonConst,
    ["min_rows_line"] = c => c.N >= MinRowsLine, ["min_pairs"] = c => c.N >= MinPairs, ["x_varies"] = c => c.Distinct(c.EncS("x")) > 1,
    ["size_nonnegative"] = c => c.Vals(c.EncS("size")).All(v => D(v) >= 0), ["size_unit_declared"] = SizeUnit,
    ["dual_measures_declared"] = DualDeclared, ["units_declared"] = Units, ["axis_labels_declared"] = AxisLabels, ["axes_distinct"] = AxesDistinct,
    ["measures_distinct"] = MeasuresDistinct,
    ["heatmap_cap"] = c => c.Dims.All(n => c.Distinct(n) <= HeatCap),
  };

  static bool Run(string output, string id, Ctx c) => output == "combo_dual_axis" && id == "time_shape" ? ShapeTime(c, 2) : Checks[id](c);

  static List<string> Rank(IReadOnlyDictionary<string, double>? scores) {
    var bc = Contract.BaseClasses;
    if (scores is null) return bc.ToList();
    double S(string b) => scores.TryGetValue(b, out var v) ? v : double.NegativeInfinity;
    return bc.Select((b, i) => (b, i)).OrderBy(t => -S(t.b)).ThenBy(t => t.i).Select(t => t.b).ToList();
  }

  /// <summary>Resolve column types with the base contract rules (explicit type honoured, else inferred).</summary>
  public static IReadOnlyList<ColumnSpec> ResolveColumns(IReadOnlyList<ColumnSpec> columns, IReadOnlyList<IReadOnlyList<object?>> rows) =>
    columns.Select((c, j) => new ColumnSpec(c.Name, FeatureExtractor.ResolveType(c.Name, rows.Select(r => r[j]).ToList(), c.Type))).ToList();

  /// <summary>Choose the concrete output for a result set. metadata: nested IReadOnlyDictionary&lt;string, object?&gt; / IReadOnlyList&lt;object?&gt; /
  /// bool / number / string (see spec/OUTPUTS_V1.md); baseScores absent = contract order; baseEligibility from <see cref="Rules.Eligible"/> (missing class = ineligible).</summary>
  public static OutputResult SpecializeOutputs(IReadOnlyList<ColumnSpec> columns, IReadOnlyList<IReadOnlyList<object?>> rows,
      IReadOnlyDictionary<string, object?>? metadata = null, IReadOnlyDictionary<string, double>? baseScores = null,
      IReadOnlyDictionary<string, string>? roles = null, IReadOnlyDictionary<string, bool>? baseEligibility = null) {
    var cols = ResolveColumns(columns, rows);
    var c = new Ctx { Cols = cols.Select(x => new Col { Name = x.Name, Type = x.Type! }).ToList(), Rows = rows, N = rows.Count, Meta = metadata, Roles = roles, El = baseEligibility ?? new Dictionary<string, bool>() };
    for (int j = 0; j < c.Cols.Count; j++) c.Idx[c.Cols[j].Name] = j;
    var rejected = new List<OutputRejection>(); var chain = new List<string>(); var seen = new HashSet<string>();
    foreach (var b in Rank(baseScores)) foreach (var o in Specialization[b]) {
      if (!seen.Add(o)) continue;
      chain.Add(o); c.Reset(); c.Output = o; c.Carriers = Specialization.Where(kv => kv.Value.Contains(o)).Select(kv => kv.Key).ToArray();
      string? reason = null;
      foreach (var p in Definitions[o]) if (!Run(o, p.Id, c)) { reason = p.Reason; break; }
      if (reason is null) {
        if (o == "table") c.Enc = new() { ["columns"] = c.Cols.Select(x => x.Name).ToList() };
        return new OutputResult(o, c.Enc, c.Params, rejected, chain);
      }
      rejected.Add(new OutputRejection(o, reason));
    }
    throw new InvalidOperationException("table is always reachable");
  }
}
