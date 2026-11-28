using System.Diagnostics;
using SqlToViz;
namespace BlazorProbe;
/// <summary>Runs the same checks in Blazor Server and WASM hosts and returns a printable report.</summary>
public static class Probe
{
    static readonly ColumnSpec[] Cols = { new("dept"), new("total") };
    static readonly IReadOnlyList<IReadOnlyList<object?>> Rows = new[] {
        (IReadOnlyList<object?>)new object?[] { "a", 10.0 }, new object?[] { "b", 20.0 }, new object?[] { "c", 5.0 } };
    const string Sql = "SELECT dept, SUM(sal) AS total FROM emp GROUP BY dept";

    public static List<string> RunRulesOnly()
    {
        var o = new List<string>(); var sw = Stopwatch.StartNew();
        var rec = new Engine().Recommend(Sql, Cols, Rows);
        o.Add($"RULES_ONLY ok final={rec.FinalClass} status={rec.ModelStatus} ms={sw.Elapsed.TotalMilliseconds:F1}");
        var plan = Preview.Recommend(Sql, new[] { new Dictionary<string, object?> { ["dept"] = "a", ["total"] = 1.0 } as IReadOnlyDictionary<string, object?> });
        o.Add($"PREVIEW ok chart={plan.ChartType}");
        return o;
    }
}
