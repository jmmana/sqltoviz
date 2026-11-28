using System.Globalization;
using MudBlazor;
namespace SqlToViz.MudBlazor;

/// <summary>Chart families the adapters can render. Anything else degrades to <see cref="Table"/>.</summary>
public enum AdapterKind { Bar, HorizontalBar, Line, Kpi, Table }

/// <summary>Simple tabular fallback (column names + cell display strings).</summary>
public sealed record TableModel(IReadOnlyList<string> Columns, IReadOnlyList<IReadOnlyList<string>> Rows);

/// <summary>Single-value card model.</summary>
public sealed record KpiModel(string Label, double Value, string Display);

/// <summary>
/// Typed model for MudBlazor. Bind <see cref="Series"/>, <see cref="XAxisLabels"/>, <see cref="Options"/> and <see cref="ChartType"/>
/// to <c>&lt;MudChart&gt;</c>. MudBlazor (8.x) has no horizontal bar type: <see cref="HorizontalBar"/> is true when the plan asked for one
/// and the model is rendered as a vertical <c>Bar</c>; hosts that need horizontal bars should use the ApexCharts config instead.
/// </summary>
public sealed record MudChartModel(
    AdapterKind Kind, ChartType? ChartType, IReadOnlyList<ChartSeries> Series, string[] XAxisLabels, ChartOptions Options,
    bool HorizontalBar, KpiModel? Kpi, TableModel? Table, IReadOnlyList<string> Notes);

/// <summary>ApexCharts options as a plain, serializable tree (System.Text.Json / Blazor-ApexCharts JS interop friendly).</summary>
public sealed record ApexConfig(IReadOnlyDictionary<string, object?> Options, AdapterKind Kind, IReadOnlyList<string> Notes);

public static class Adapters
{
    static double? Num(object? v)
    {
        if (v is not (byte or sbyte or short or ushort or int or uint or long or ulong or float or double or decimal)) return null;
        double d = Convert.ToDouble(v, CultureInfo.InvariantCulture);
        return double.IsFinite(d) ? d : null;
    }

    /// <summary>Plan chosen from a model-backed Recommendation: x = first x_axis role, y = first numeric y_axis role.</summary>
    public static Plan PlanFrom(Recommendation rec, IReadOnlyList<ColumnSpec> columns, IReadOnlyList<IReadOnlyList<object?>> rows)
    {
        ArgumentNullException.ThrowIfNull(rec);
        string cls = rec.FinalClass;
        var roles = rec.Roles ?? [];
        bool Numeric(int j) => rows.Count > 0 && rows.All(r => r[j] is null || Num(r[j]).HasValue);
        string? x = null, y = null;
        for (int j = 0; j < roles.Count; j++)
        {
            if (x is null && roles[j].Role == "x_axis") x = roles[j].Column;
            if (y is null && roles[j].Role == "y_axis" && Numeric(j)) y = roles[j].Column;
        }
        if (cls == "kpi")
        {
            y ??= columns.Select((c, j) => (c, j)).Where(t => Numeric(t.j)).Select(t => t.c.Name).FirstOrDefault();
            return new Plan("kpi", null, y, "Model recommendation", "model");
        }
        if (cls is "bar" or "horizontal_bar" or "line" && x is not null && y is not null && x != y)
            return new Plan(cls, x, y, "Model recommendation", "model");
        return new Plan("table", null, null, cls is "bar" or "horizontal_bar" or "line" or "kpi" ? "Roles unresolved" : $"No adapter for '{cls}'", "model");
    }

    static IReadOnlyDictionary<string, object?> AsDict(IReadOnlyList<ColumnSpec> cols, IReadOnlyList<object?> row)
    {
        var d = new Dictionary<string, object?>(cols.Count);
        for (int j = 0; j < cols.Count; j++) d[cols[j].Name] = row[j];
        return d;
    }

    public static IReadOnlyList<IReadOnlyDictionary<string, object?>> ToDicts(IReadOnlyList<ColumnSpec> cols, IReadOnlyList<IReadOnlyList<object?>> rows)
        => rows.Select(r => AsDict(cols, r)).ToArray();

    static string Display(object? v) => v switch
    {
        null => "", IFormattable f => f.ToString(null, CultureInfo.InvariantCulture), _ => v.ToString() ?? "",
    };

    static bool Supported(Plan p, IReadOnlyList<IReadOnlyDictionary<string, object?>> rows) =>
        rows.Count > 0 && p.ChartType switch
        {
            "bar" or "horizontal_bar" or "line" => p.X is not null && p.Y is not null && rows.All(r => r.ContainsKey(p.X) && r.ContainsKey(p.Y)),
            "kpi" => p.Y is not null && rows.Count == 1 && rows[0].ContainsKey(p.Y) && Num(rows[0][p.Y]).HasValue,
            _ => false,
        };

    static TableModel ToTable(IReadOnlyList<IReadOnlyDictionary<string, object?>> rows)
    {
        var cols = rows.Count == 0 ? [] : rows[0].Keys.ToArray();
        return new TableModel(cols, rows.Select(r => (IReadOnlyList<string>)cols.Select(c => r.TryGetValue(c, out var v) ? Display(v) : "").ToArray()).ToArray());
    }

    /// <summary>Builds the MudBlazor model. Unsupported plans (or missing columns) fall back to a table with a note; never throws on a valid Plan.</summary>
    public static MudChartModel ToMudBlazor(Plan plan, IReadOnlyList<IReadOnlyDictionary<string, object?>> rows)
    {
        ArgumentNullException.ThrowIfNull(plan); ArgumentNullException.ThrowIfNull(rows);
        var notes = new List<string>();
        if (!Supported(plan, rows))
        {
            notes.Add(plan.ChartType == "table" ? "Table recommended." : $"Chart '{plan.ChartType}' is not supported by the MudBlazor adapter; showing a table.");
            return new MudChartModel(AdapterKind.Table, null, [], [], new ChartOptions(), false, null, ToTable(rows), notes);
        }
        if (plan.ChartType == "kpi")
        {
            double v = Num(rows[0][plan.Y!])!.Value;
            return new MudChartModel(AdapterKind.Kpi, null, [], [], new ChartOptions(), false, new KpiModel(plan.Y!, v, v.ToString("G", CultureInfo.InvariantCulture)), null, notes);
        }
        var labels = rows.Select(r => Display(r[plan.X!])).ToArray();
        var data = new double[rows.Count];
        int dropped = 0;
        for (int i = 0; i < rows.Count; i++)
        {
            var n = Num(rows[i][plan.Y!]);
            if (n is null) dropped++;
            data[i] = n ?? 0d;
        }
        if (dropped > 0) notes.Add($"{dropped} non-numeric/NULL value(s) plotted as 0.");
        bool horizontal = plan.ChartType == "horizontal_bar";
        if (horizontal) notes.Add("MudBlazor has no horizontal bar; rendered as a vertical Bar.");
        var type = plan.ChartType == "line" ? ChartType.Line : ChartType.Bar;
        var opts = new ChartOptions { YAxisTicks = 5, ShowLegend = false };
        return new MudChartModel(horizontal ? AdapterKind.HorizontalBar : plan.ChartType == "line" ? AdapterKind.Line : AdapterKind.Bar, type,
            [new ChartSeries { Name = plan.Y!, Data = data }], labels, opts, horizontal, null, null, notes);
    }

    /// <summary>
    /// Complete ApexCharts options for bar / horizontal_bar / line: chart type, title, axis titles, tooltip, data labels, legend,
    /// stroke, x-axis type (category), series and an <c>noData</c> message. KPI and table plans return Kind=Table/Kpi with minimal options.
    /// </summary>
    public static ApexConfig ToApexConfig(Plan plan, IReadOnlyList<IReadOnlyDictionary<string, object?>> rows, string? title = null)
    {
        ArgumentNullException.ThrowIfNull(plan); ArgumentNullException.ThrowIfNull(rows);
        var notes = new List<string>();
        if (!Supported(plan, rows) || plan.ChartType == "kpi")
        {
            var kind = Supported(plan, rows) ? AdapterKind.Kpi : AdapterKind.Table;
            notes.Add(kind == AdapterKind.Kpi ? "Render the value as a card; ApexCharts has no KPI series." : $"No ApexCharts mapping for '{plan.ChartType}'; render a table.");
            return new ApexConfig(new Dictionary<string, object?> { ["noData"] = new Dictionary<string, object?> { ["text"] = "No chart for this result" } }, kind, notes);
        }
        bool line = plan.ChartType == "line", horizontal = plan.ChartType == "horizontal_bar";
        var categories = rows.Select(r => Display(r[plan.X!])).ToArray();
        var data = rows.Select(r => (object?)Num(r[plan.Y!])).ToArray();
        var options = new Dictionary<string, object?>
        {
            ["chart"] = new Dictionary<string, object?> { ["type"] = line ? "line" : "bar", ["toolbar"] = new Dictionary<string, object?> { ["show"] = false }, ["animations"] = new Dictionary<string, object?> { ["enabled"] = false } },
            ["plotOptions"] = new Dictionary<string, object?> { ["bar"] = new Dictionary<string, object?> { ["horizontal"] = horizontal } },
            ["title"] = new Dictionary<string, object?> { ["text"] = title ?? plan.Y },
            ["xaxis"] = new Dictionary<string, object?> { ["type"] = "category", ["categories"] = categories, ["title"] = new Dictionary<string, object?> { ["text"] = horizontal ? plan.Y : plan.X } },
            ["yaxis"] = new Dictionary<string, object?> { ["title"] = new Dictionary<string, object?> { ["text"] = horizontal ? plan.X : plan.Y } },
            ["dataLabels"] = new Dictionary<string, object?> { ["enabled"] = !line && rows.Count <= 12 },
            ["stroke"] = new Dictionary<string, object?> { ["curve"] = "straight", ["width"] = line ? 2 : 0 },
            ["legend"] = new Dictionary<string, object?> { ["show"] = false },
            ["tooltip"] = new Dictionary<string, object?> { ["enabled"] = true },
            ["noData"] = new Dictionary<string, object?> { ["text"] = "No data" },
            ["series"] = new object[] { new Dictionary<string, object?> { ["name"] = plan.Y, ["data"] = data } },
        };
        if (data.Any(d => d is null)) notes.Add("NULL/non-numeric values are emitted as null (gaps).");
        return new ApexConfig(options, line ? AdapterKind.Line : horizontal ? AdapterKind.HorizontalBar : AdapterKind.Bar, notes);
    }
}
