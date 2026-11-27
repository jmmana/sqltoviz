// Rules-only baseline and hard semantic constraints over the 10 base classes (port of the Python/reference rules).
namespace SqlToViz;
public static class Rules {
  static readonly Dictionary<string, int> T = BuildT();
  static readonly Dictionary<string, int> Col = Contract.ColumnFeatures.Select((f, i) => (f.Name, i)).ToDictionary(x => x.Name, x => x.i);
  static Dictionary<string, int> BuildT() { var d = new Dictionary<string, int>(); for (int i = 0; i < 16; i++) d[Contract.SqlFeatures[i].Name] = i; for (int i = 0; i < 16; i++) d[Contract.GlobalFeatures[i].Name] = 16 + i; return d; }
  const double DonutMaxK = 5, HeatmapMinK = 6, LongLabel = 20.0 / 50.0; const int BarMaxRows = 25, ScatterMinRows = 15;
  sealed record V(double Single, int M, int Nom, int Quant, int Temp, double Crossed, double MinK, int Rows, float[][] Q, float[][] N);
  static V View(float[] t, float[][] c) {
    double g(string n) => t[T[n]];
    return new V(g("single_row"), (int)Math.Round(g("column_count")), (int)Math.Round(g("nominal_count")), (int)Math.Round(g("quantitative_count")), (int)Math.Round(g("temporal_count")),
      g("crossed_structure"), g("min_nominal_cardinality"), (int)Math.Round(Math.Pow(10, g("log_row_count")) - 1),
      c.Where(r => r[Col["is_quantitative"]] == 1).ToArray(), c.Where(r => r[Col["is_nominal"]] == 1).ToArray());
  }
  public static string Predict(float[] t, float[][] c) {
    var v = View(t, c);
    bool nonneg = v.Q.Length > 0 && v.Q.All(r => r[Col["negative_ratio"]] == 0);
    if (v.Single == 1 && v.M <= 3 && v.Quant >= 1) return "kpi";
    if (v.M >= 6) return "table";
    if (v.Crossed == 1) return v.MinK >= HeatmapMinK ? "heatmap" : "stacked_bar";
    if (v.M == 2 && v.Temp == 1 && v.Quant == 1) return nonneg ? "area" : "line";
    if (v.Quant >= 2 && v.Nom == 0 && v.Temp == 0 && v.Rows >= ScatterMinRows) return "scatter";
    if (v.M == 2 && v.Nom == 1 && v.Quant == 1) {
      bool zeroAll = v.Q.Length > 0 && v.Q.All(r => r[Col["zero_ratio"]] == 1);
      if (v.MinK <= DonutMaxK && nonneg && !zeroAll) return "donut";
      if (v.N.Length > 0 && v.N[0][Col["mean_string_length"]] >= LongLabel) return "horizontal_bar";
      return v.Rows <= BarMaxRows ? "bar" : "table";
    }
    return "table";
  }
  public static IReadOnlyDictionary<string, bool> Eligible(float[] t, float[][] c) {
    var v = View(t, c);
    bool nonneg = v.Q.Length > 0 && v.Q.All(r => r[Col["negative_ratio"]] == 0), positiveTotal = v.Q.Length > 0 && v.Q.Any(r => r[Col["zero_ratio"]] < 1);
    bool catMeasure = v.Nom >= 1 && v.Quant >= 1 && v.Rows >= 2;
    return new Dictionary<string, bool> {
      ["kpi"] = v.Single == 1 && v.Quant >= 1 && v.M <= 3, ["bar"] = catMeasure, ["horizontal_bar"] = catMeasure,
      ["stacked_bar"] = v.Nom >= 2 && v.Quant >= 1 && nonneg && v.Rows >= 4,
      ["line"] = v.Temp >= 1 && v.Quant >= 1 && v.Rows >= 3, ["area"] = v.Temp >= 1 && v.Quant >= 1 && nonneg && v.Rows >= 3,
      ["donut"] = v.Nom >= 1 && v.Quant >= 1 && nonneg && positiveTotal && v.MinK >= 2 && v.MinK <= 12,
      ["scatter"] = v.Quant >= 2 && v.Rows >= 3, ["heatmap"] = v.Nom >= 2 && v.Quant >= 1, ["table"] = true };
  }
  /// <summary>Highest-scoring eligible class (stable on ties), else table.</summary>
  public static (string Class, bool Changed) ConstrainedChoice(IReadOnlyList<double> scores, float[] t, float[][] c) {
    var el = Eligible(t, c);
    var order = Enumerable.Range(0, scores.Count).OrderByDescending(k => scores[k]).ThenBy(k => k).ToArray();
    foreach (var k in order) if (el[Contract.BaseClasses[k]]) return (Contract.BaseClasses[k], k != order[0]);
    return ("table", true);
  }
}
