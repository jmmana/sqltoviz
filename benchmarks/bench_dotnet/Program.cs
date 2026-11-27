// SDK benchmark (.NET). Same JSON schema/scenarios as bench_python.py. Usage: dotnet run -c Release --project benchmarks/bench_dotnet -- OUT.json [reps]  |  internal: --child N
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json;
using SqlToViz;
using SqlToViz.Onnx;
const string Sql = "SELECT category, region, SUM(value) AS value, day FROM t GROUP BY category, region, day ORDER BY day";
var schema = new[] { new ColumnSpec("category"), new ColumnSpec("region"), new ColumnSpec("value"), new ColumnSpec("day") };
int[] sizes = { 10, 100, 1000, 10000 };
static List<IReadOnlyList<object?>> Rows(int n) => Enumerable.Range(0, n).Select(i => (IReadOnlyList<object?>)new object?[] { $"cat{(i * 7) % 12}", $"reg{(i * 3) % 5}", ((i * 37) % 1000) + ((i * 13) % 100) / 100.0, $"2024-{1 + i % 12:00}-{1 + i % 27:00}" }).ToList();
static double Pct(List<double> a, double q) { a.Sort(); double k = (a.Count - 1) * q / 100; int lo = (int)k; return a[lo] + (a[Math.Min(lo + 1, a.Count - 1)] - a[lo]) * (k - lo); }
static OnnxRunner Chart() {
  var asm = typeof(OnnxEngine).Assembly;
  byte[] Read(string n) { using var s = asm.GetManifestResourceStream("SqlToViz.Onnx.models." + n)!; using var ms = new MemoryStream(); s.CopyTo(ms); return ms.ToArray(); }
  using var man = JsonDocument.Parse(Read("manifest.json")); var c = man.RootElement.GetProperty("chart");
  return OnnxRunner.Create(Read(c.GetProperty("file").GetString()!), c.GetProperty("sha256").GetString()!, ModelKind.Chart);
}
(double, double, double) One(OnnxRunner chart, List<IReadOnlyList<object?>> rows) {
  long t0 = Stopwatch.GetTimestamp(); var ex = FeatureExtractor.Extract(Sql, schema, rows); long t1 = Stopwatch.GetTimestamp();
  var s = chart.Run(ex.Table, 1, 32).Select(v => (double)v).ToArray(); long t2 = Stopwatch.GetTimestamp();
  Rules.ConstrainedChoice(s, ex.Table, ex.Columns); long t3 = Stopwatch.GetTimestamp();
  double ms(long a, long b) => (b - a) * 1000.0 / Stopwatch.Frequency; return (ms(t0, t1), ms(t1, t2), ms(t2, t3));
}
if (args.Length > 1 && args[0] == "--child") {
  int n = int.Parse(args[1]); using var chart = Chart(); var rows = Rows(n); One(chart, rows);
  long b = PeakRss(); for (int i = 0; i < 30; i++) One(chart, rows);
  Console.WriteLine(JsonSerializer.Serialize(new { baseline = b, peak = PeakRss() })); return;
}
// peak resident set size in bytes (getrusage on macOS/Linux, like the Python and Node benchmarks)
static long PeakRss() {
  if (OperatingSystem.IsWindows()) { var p = Process.GetCurrentProcess(); p.Refresh(); return p.PeakWorkingSet64; }
  var buf = new byte[256]; getrusage(0, buf); long v = BitConverter.ToInt64(buf, 32);
  return OperatingSystem.IsMacOS() ? v : v * 1024;
}
[System.Runtime.InteropServices.DllImport("libc", SetLastError = true)] static extern int getrusage(int who, byte[] usage);
string outFile = args[0]; int reps = args.Length > 1 ? int.Parse(args[1]) : 400;
var sw = Stopwatch.StartNew(); var engine = OnnxEngine.LoadDefault(); double loadMs = sw.Elapsed.TotalMilliseconds; engine.GetType();
using var runner = Chart();
var result = new Dictionary<string, object> {
  ["sdk"] = "dotnet", ["environment"] = new { cpu = RuntimeInformation.ProcessArchitecture.ToString(), os = RuntimeInformation.OSDescription, runtime = RuntimeInformation.FrameworkDescription, onnxruntime = "Microsoft.ML.OnnxRuntime", threads = 1 },
  ["load"] = new { import_ms = 0.0, engine_load_ms = loadMs, note = "OnnxEngine.LoadDefault(): checksum + 2 sessions from embedded resources (cold, first call incl. JIT)" } };
var res = new Dictionary<string, object>();
foreach (int n in sizes) {
  var rows = Rows(n); int k = n <= 1000 ? reps : Math.Max(reps / 8, 40);
  for (int i = 0; i < 20; i++) One(runner, rows);
  var ex = new List<double>(); var inf = new List<double>(); var con = new List<double>(); var tot = new List<double>();
  for (int i = 0; i < k; i++) { var (a, b, c) = One(runner, rows); ex.Add(a); inf.Add(b); con.Add(c); tot.Add(a + b + c); }
  var exe = Environment.ProcessPath!; bool viaHost = Path.GetFileNameWithoutExtension(exe).Equals("dotnet", StringComparison.OrdinalIgnoreCase);
  var psi = new ProcessStartInfo(exe, viaHost ? $"\"{typeof(Program).Assembly.Location}\" --child {n}" : $"--child {n}") { RedirectStandardOutput = true };
  using var child = Process.Start(psi)!; var m = JsonDocument.Parse(child.StandardOutput.ReadToEnd()).RootElement; child.WaitForExit();
  double peak = m.GetProperty("peak").GetDouble(), bl = m.GetProperty("baseline").GetDouble();
  res[n.ToString()] = new { runs = k, extract_ms = new { median = Pct(ex, 50), p95 = Pct(ex, 95), p99 = Pct(ex, 99) }, onnx_ms = new { median = Pct(inf, 50), p95 = Pct(inf, 95) },
    constraints_ms = new { median = Pct(con, 50), p95 = Pct(con, 95) }, end_to_end_ms = new { median = Pct(tot, 50), p95 = Pct(tot, 95), p99 = Pct(tot, 99) }, peak_rss_mb = peak / 1e6, rss_growth_mb = (peak - bl) / 1e6 };
}
result["sizes"] = res;
File.WriteAllText(outFile, JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine(JsonSerializer.Serialize(res.ToDictionary(kv => kv.Key, kv => Math.Round(JsonDocument.Parse(JsonSerializer.Serialize(kv.Value)).RootElement.GetProperty("end_to_end_ms").GetProperty("median").GetDouble(), 3))) + " load_ms " + Math.Round(loadMs, 1));
