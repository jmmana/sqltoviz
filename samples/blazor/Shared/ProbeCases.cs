using SqlToViz;
namespace BlazorProbe;
public static class ProbeCases
{
    public static readonly (string Sql, ColumnSpec[] Cols, IReadOnlyList<IReadOnlyList<object?>> Rows)[] All =
    {
        ("SELECT SUM(x) AS s FROM t", new[] { new ColumnSpec("s") }, new[] { (IReadOnlyList<object?>)new object?[] { 3L } }),
        ("SELECT dept, SUM(sal) AS total FROM emp GROUP BY dept", new[] { new ColumnSpec("dept"), new ColumnSpec("total") },
            new[] { (IReadOnlyList<object?>)new object?[] { "a", 10.0 }, new object?[] { "b", 20.0 }, new object?[] { "c", 5.0 } }),
        ("SELECT d, v FROM m ORDER BY d", new[] { new ColumnSpec("d", "temporal"), new ColumnSpec("v") },
            new[] { (IReadOnlyList<object?>)new object?[] { "2024-01-01", 1.0 }, new object?[] { "2024-01-02", 3.0 }, new object?[] { "2024-01-03", 2.0 }, new object?[] { "2024-01-04", 5.0 } }),
    };
    /// <summary>Stable one-line summary used to compare hosts (class + rounded chart scores).</summary>
    public static string Summary(Recommendation r) =>
        $"final={r.FinalClass} base={r.BaseClass} status={r.ModelStatus} scores=" + string.Join(",", r.Scores!.Values.Select(v => v.ToString("F4", System.Globalization.CultureInfo.InvariantCulture)));
}
