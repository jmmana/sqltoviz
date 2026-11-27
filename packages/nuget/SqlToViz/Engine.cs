// Model-backed recommendation engine. Learned models are injected as IModelRunner, so the public API is identical for the bundled
// EXPERIMENTAL candidate models and for future final models (load different files / a different manifest).
namespace SqlToViz;
/// <summary>Runs a float32 model: input is rows x cols (row-major); returns rows x outputs (row-major).</summary>
public interface IModelRunner { float[] Run(float[] input, int rows, int cols); }
public sealed record RoleResult(string Column, string Role, double[] Scores);
public sealed record Recommendation(string ContractVersion, string ContractSha256, string ModelStatus, string BaseClass, string FinalClass, bool ConstraintChanged,
  string RuleClass, IReadOnlyDictionary<string, double>? Scores, IReadOnlyDictionary<string, bool> Eligible, IReadOnlyList<RoleResult>? Roles,
  float[] TableFeatures, float[][] ColumnFeatures, IReadOnlyList<string> Warnings);
public sealed class Engine(IModelRunner? chart = null, IModelRunner? role = null, string? chartStatus = null) {
  public string ModelStatus => chart is null ? "none (rules only)" : chartStatus ?? "unknown";
  static int ArgMax(IReadOnlyList<double> a) { int k = 0; for (int i = 1; i < a.Count; i++) if (a[i] > a[k]) k = i; return k; }
  public Recommendation Recommend(string sql, IReadOnlyList<ColumnSpec> columns, IReadOnlyList<IReadOnlyList<object?>> rows) {
    var ex = FeatureExtractor.Extract(sql, columns, rows);
    string ruleClass = Rules.Predict(ex.Table, ex.Columns), baseClass = ruleClass, final = ruleClass; bool changed = false;
    var el = Rules.Eligible(ex.Table, ex.Columns); var warnings = new List<string>(); Dictionary<string, double>? scores = null;
    if (chart is null) warnings.Add("No chart model loaded: rules-only recommendation.");
    else {
      var raw = chart.Run(ex.Table, 1, 32).Take(Contract.BaseClasses.Length).Select(v => (double)v).ToArray();
      baseClass = Contract.BaseClasses[ArgMax(raw)];
      (final, changed) = Rules.ConstrainedChoice(raw, ex.Table, ex.Columns);
      scores = Contract.BaseClasses.Select((k, i) => (k, raw[i])).ToDictionary(x => x.k, x => x.Item2);
    }
    List<RoleResult>? roles = null;
    if (role is not null) {
      var flat = new float[ex.Columns.Length * 28]; for (int j = 0; j < ex.Columns.Length; j++) ex.Columns[j].CopyTo(flat, j * 28);
      var outp = role.Run(flat, ex.Columns.Length, 28);
      roles = columns.Select((c, j) => { var s = Enumerable.Range(0, 5).Select(i => (double)outp[j * 5 + i]).ToArray(); return new RoleResult(c.Name, Contract.Roles[ArgMax(s)], s); }).ToList();
    }
    var status = ModelStatus;
    if (status != "validated") warnings.Add($"Model status: {status}. Recommendations are not scientifically validated.");
    return new Recommendation(Contract.Version, Contract.Sha256, status, baseClass, final, changed, ruleClass, scores, el, roles, ex.Table, ex.Columns, warnings);
  }
}
