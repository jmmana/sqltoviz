// ONNX runtime integration for SqlToViz. Models are checksum- and schema-validated; the bundled candidates are EXPERIMENTAL and
// replaceable by files/manifest without changing the public API.
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.ML.OnnxRuntime;
using Microsoft.ML.OnnxRuntime.Tensors;
namespace SqlToViz.Onnx;

public sealed class ModelException(string message) : InvalidOperationException(message);
public enum ModelKind { Chart, Role }
public sealed record ModelManifestEntry(string File, string Sha256, string Status, string? Version = null);

public sealed class OnnxRunner : IModelRunner, IDisposable {
  readonly InferenceSession session; readonly string input, output; readonly int inWidth, outWidth;
  OnnxRunner(InferenceSession s, string i, string o, int iw, int ow) { session = s; input = i; output = o; inWidth = iw; outWidth = ow; }
  public static OnnxRunner Create(byte[] model, string expectedSha256, ModelKind kind) {
    var sha = Convert.ToHexString(SHA256.HashData(model)).ToLowerInvariant();
    if (string.IsNullOrEmpty(expectedSha256) || sha != expectedSha256.ToLowerInvariant()) throw new ModelException("model checksum mismatch");
    var (i, o, iw, ow) = kind == ModelKind.Chart ? ("table_features", "chart_scores", 32, 10) : ("column_features", "role_scores", 28, 5);
    var opts = new SessionOptions { IntraOpNumThreads = 1, InterOpNumThreads = 1 };
    var s = new InferenceSession(model, opts);
    if (s.InputMetadata.Count != 1 || !s.InputMetadata.TryGetValue(i, out var im) || im.ElementType != typeof(float) || im.Dimensions.Length != 2 || im.Dimensions[1] != iw ||
        s.OutputMetadata.Count != 1 || !s.OutputMetadata.TryGetValue(o, out var om) || om.ElementType != typeof(float) || om.Dimensions.Length != 2 || om.Dimensions[1] != ow) {
      s.Dispose(); throw new ModelException("incompatible model schema");
    }
    var r = new OnnxRunner(s, i, o, iw, ow);
    r.Run(new float[iw], 1, iw);                                  // probe run
    return r;
  }
  public float[] Run(float[] data, int rows, int cols) {
    if (cols != inWidth) throw new ModelException($"expected {inWidth} input columns");
    using var results = session.Run(new[] { NamedOnnxValue.CreateFromTensor(input, new DenseTensor<float>(data, new[] { rows, cols })) });
    var t = results.First(r => r.Name == output).AsTensor<float>();
    if (t.Dimensions.Length != 2 || t.Dimensions[0] != rows || t.Dimensions[1] != outWidth) throw new ModelException("incompatible model output");
    return t.ToArray();
  }
  public void Dispose() => session.Dispose();
}

public static class OnnxEngine {
  /// <summary>Engine from a manifest JSON ({"chart":{file,sha256,status},"role":{...}}) and a reader that returns the bytes of each file.</summary>
  public static Engine Load(string manifestJson, Func<string, byte[]> readFile) {
    using var doc = JsonDocument.Parse(manifestJson);
    ModelManifestEntry? Entry(string k) => doc.RootElement.TryGetProperty(k, out var e)
      ? new ModelManifestEntry(e.GetProperty("file").GetString()!, e.GetProperty("sha256").GetString()!, e.GetProperty("status").GetString()!) : null;
    var chart = Entry("chart"); var role = Entry("role");
    return new Engine(chart is null ? null : OnnxRunner.Create(readFile(chart.File), chart.Sha256, ModelKind.Chart),
                      role is null ? null : OnnxRunner.Create(readFile(role.File), role.Sha256, ModelKind.Role), chart?.Status);
  }
  /// <summary>Engine from a manifest.json inside <paramref name="directory"/> (use this to plug in final models).</summary>
  public static Engine LoadFromDirectory(string directory) => Load(File.ReadAllText(Path.Combine(directory, "manifest.json")), f => File.ReadAllBytes(Path.Combine(directory, f)));
  /// <summary>Engine with the bundled EXPERIMENTAL candidate models (checksum-verified).</summary>
  public static Engine LoadDefault() {
    var asm = typeof(OnnxEngine).Assembly;
    byte[] Read(string name) { using var s = asm.GetManifestResourceStream("SqlToViz.Onnx.models." + name) ?? throw new ModelException("bundled model missing: " + name); using var ms = new MemoryStream(); s.CopyTo(ms); return ms.ToArray(); }
    return Load(System.Text.Encoding.UTF8.GetString(Read("manifest.json")), Read);
  }
}
