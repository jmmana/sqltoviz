using System.Diagnostics;
using SqlToViz;
using SqlToViz.Onnx;
namespace BlazorProbe;
public static class ProbeOnnx
{
    public static List<string> Run()
    {
        var o = new List<string>();
        try
        {
            var sw = Stopwatch.StartNew();
            var engine = OnnxEngine.LoadDefault();
            double load = sw.Elapsed.TotalMilliseconds; sw.Restart();
            var rec = engine.Recommend("SELECT SUM(x) AS s FROM t", new[] { new ColumnSpec("s") }, new[] { (IReadOnlyList<object?>)new object?[] { 3L } });
            o.Add($"ONNX ok final={rec.FinalClass} status={rec.ModelStatus} load_ms={load:F1} run_ms={sw.Elapsed.TotalMilliseconds:F1}");
        }
        catch (Exception e) { o.Add($"ONNX FAILED {e.GetType().Name}: {e.Message}"); }
        return o;
    }
}
