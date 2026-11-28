// SqlVizSpec-v1.0.0 feature engine (no dependencies). Port of the Python/reference implementation; behaviour is pinned by
// parity/golden_v1.json and the nine confirmed interpretations (research/kaggle/FEATURE_INTERPRETATIONS.md).
using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;
namespace SqlToViz;

public sealed record ColumnSpec(string Name, string? Type = null);
public sealed record Extracted(float[] Table, float[][] Columns);
/// <summary>Input rejected by the contract (malformed SQL lexing, bad types, out-of-bounds).</summary>
public sealed class FeatureException(string message) : ArgumentException(message);

public static class FeatureExtractor {
  const double SafeInt = 9007199254740991d;

  // ------------------------------------------------------------------ lexer
  internal sealed record Tok(string Kind, string Text, string Norm, int Depth);
  static bool IsSpace(int cp) => (cp >= 0x09 && cp <= 0x0d) || (cp >= 0x1c && cp <= 0x20) || cp == 0x85 || cp == 0xa0 || cp == 0x1680 ||
    (cp >= 0x2000 && cp <= 0x200a) || cp == 0x2028 || cp == 0x2029 || cp == 0x202f || cp == 0x205f || cp == 0x3000;
  static bool Digit(char c) => c >= '0' && c <= '9';
  static bool WordStart(char c) => (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || c == '_';
  static bool WordPart(char c) => WordStart(c) || Digit(c) || c == '$';
  static bool AllDigits(string s) => s.Length > 0 && s.All(Digit);

  internal static List<Tok> Lex(string sql) {
    var toks = new List<Tok>();
    int i = 0, depth = 0, n = sql.Length;
    while (i < n) {
      int cp = char.IsHighSurrogate(sql[i]) && i + 1 < n && char.IsLowSurrogate(sql[i + 1]) ? char.ConvertToUtf32(sql[i], sql[i + 1]) : sql[i];
      int w = cp > 0xFFFF ? 2 : 1;
      char c = sql[i];
      if (IsSpace(cp)) { i += w; continue; }
      if (string.CompareOrdinal(sql, i, "--", 0, 2) == 0) { int j = sql.IndexOf('\n', i); i = j < 0 ? n : j + 1; continue; }
      if (string.CompareOrdinal(sql, i, "/*", 0, 2) == 0) {
        int j = sql.IndexOf("*/", i + 2, StringComparison.Ordinal);
        if (j < 0) throw new FeatureException("unclosed block comment");
        i = j + 2; continue;
      }
      if (c == '\'' || c == '"' || c == '`') {
        int j = i + 1; var buf = new StringBuilder();
        for (;;) {
          if (j >= n) throw new FeatureException("unclosed quote");
          if (sql[j] == c) {
            if (j + 1 < n && sql[j + 1] == c) { buf.Append(c); j += 2; continue; }
            break;
          }
          buf.Append(sql[j]); j++;
        }
        toks.Add(new(c == '\'' ? "string" : "quoted", sql.Substring(i, j + 1 - i), buf.ToString(), depth));
        i = j + 1; continue;
      }
      if (c == '[') {
        int j = sql.IndexOf(']', i + 1);
        if (j < 0) throw new FeatureException("unclosed bracket identifier");
        toks.Add(new("quoted", sql.Substring(i, j + 1 - i), sql.Substring(i + 1, j - i - 1), depth));
        i = j + 1; continue;
      }
      if (WordStart(c)) {
        int j = i + 1; while (j < n && WordPart(sql[j])) j++;
        var word = sql.Substring(i, j - i);
        toks.Add(new("word", word, word.ToUpperInvariant(), depth)); i = j; continue;
      }
      int e = NumberEnd(sql, i);
      if (e > i) { var t = sql.Substring(i, e - i); toks.Add(new("number", t, t, depth)); i = e; continue; }
      string text = sql.Substring(i, w);
      if (c == '(') { toks.Add(new("punct", text, text, depth)); depth++; }
      else if (c == ')') { depth = Math.Max(depth - 1, 0); toks.Add(new("punct", text, text, depth)); }
      else toks.Add(new("punct", text, text, depth));
      i += w;
    }
    return toks;
  }
  // (?:[0-9]+\.[0-9]*|\.[0-9]+|[0-9]+)(?:[eE][+-]?[0-9]+)?  - returns end index or i when no number starts here
  static int NumberEnd(string s, int i) {
    int n = s.Length, j = i;
    if (Digit(s[j])) { while (j < n && Digit(s[j])) j++; if (j < n && s[j] == '.') { j++; while (j < n && Digit(s[j])) j++; } }
    else if (s[j] == '.' && j + 1 < n && Digit(s[j + 1])) { j++; while (j < n && Digit(s[j])) j++; }
    else return i;
    if (j < n && (s[j] == 'e' || s[j] == 'E')) {
      int k = j + 1; if (k < n && (s[k] == '+' || s[k] == '-')) k++;
      if (k < n && Digit(s[k])) { while (k < n && Digit(s[k])) k++; j = k; }
    }
    return j;
  }

  static bool Kw(Tok t, params string[] names) => t.Kind == "word" && Array.IndexOf(names, t.Norm) >= 0;
  static readonly HashSet<string> ClauseEndSet = new() { "HAVING", "ORDER", "LIMIT", "OFFSET", "FETCH", "UNION", "INTERSECT", "EXCEPT", "WINDOW" };
  static readonly string[] SetOps = { "UNION", "INTERSECT", "EXCEPT" };
  static readonly string[] Agg = { "SUM", "COUNT", "AVG", "MIN", "MAX" };
  static readonly string[] TemporalFn = { "DATE_TRUNC", "EXTRACT", "YEAR", "MONTH", "DAY", "STRFTIME", "DATEPART" };
  static readonly HashSet<string> OperandBlock = new() { "SELECT", "AND", "OR", "NOT", "WHEN", "THEN", "ELSE", "CASE", "IN", "BETWEEN", "LIKE", "IS", "ON", "WHERE", "BY", "HAVING", "DISTINCT", "ALL", "AS", "BEGIN", "EXISTS" };
  static bool FollowedByParen(List<Tok> t, int i) => i + 1 < t.Count && t[i + 1].Kind == "punct" && t[i + 1].Text == "(";

  static int ClauseEnd(List<Tok> toks, int start) {
    int d = start < toks.Count ? toks[start].Depth : 0, j = start;
    while (j < toks.Count) {
      var t = toks[j];
      if (t.Depth < d || (t.Kind == "punct" && t.Text == ")" && t.Depth < d)) break;
      if (t.Kind == "punct" && t.Text == ";") break;
      if (t.Depth == d && t.Kind == "word" && ClauseEndSet.Contains(t.Norm)) break;
      j++;
    }
    return j;
  }
  static List<List<Tok>> SplitCommas(List<Tok> toks, int a, int b) {
    var res = new List<List<Tok>>();
    if (a >= b) return res;
    int d = int.MaxValue; for (int k = a; k < b; k++) d = Math.Min(d, toks[k].Depth);
    var cur = new List<Tok>();
    for (int k = a; k < b; k++) {
      var t = toks[k];
      if (t.Kind == "punct" && t.Text == "," && t.Depth == d) { res.Add(cur); cur = new(); } else cur.Add(t);
    }
    res.Add(cur);
    return res.Where(e => e.Count > 0).ToList();
  }
  static int? OuterSelect(List<Tok> toks) {
    var sel = new List<int>(); for (int i = 0; i < toks.Count; i++) if (Kw(toks[i], "SELECT")) sel.Add(i);
    if (sel.Count == 0) return null;
    int dmin = sel.Min(i => toks[i].Depth);
    foreach (var i in sel) if (toks[i].Depth == dmin) return i;
    return null;
  }
  static (int, int) ProjectionSpan(List<Tok> toks, int s) {
    int a = s + 1, d = toks[s].Depth;
    while (a < toks.Count && toks[a].Depth == d && Kw(toks[a], "DISTINCT", "ALL")) a++;
    if (a + 1 < toks.Count && Kw(toks[a], "TOP") && toks[a + 1].Kind == "number") a += 2;
    int b = a;
    while (b < toks.Count) {
      var t = toks[b];
      if (t.Depth < d || (t.Kind == "punct" && t.Text == ";")) break;
      if (t.Depth == d && (Kw(t, "FROM") || Kw(t, SetOps))) break;
      b++;
    }
    return (a, b);
  }
  static (int, int) OuterRange(List<Tok> toks, int s) {
    int d = toks[s].Depth;
    for (int j = s + 1; j < toks.Count; j++) {
      if (toks[j].Depth < d) return (s, j);
      if (toks[j].Depth == d && Kw(toks[j], SetOps)) return (s, j);
    }
    return (s, toks.Count);
  }
  static List<Tok> ExprAndAlias(List<Tok> expr) {
    var last = expr[^1];
    if (expr.Count >= 3 && Kw(expr[^2], "AS") && expr[^2].Depth == last.Depth && (last.Kind is "word" or "quoted" or "string")) return expr.GetRange(0, expr.Count - 2);
    if (expr.Count >= 2 && (last.Kind is "word" or "quoted") && last.Depth == expr[0].Depth) {
      var p = expr[^2];
      bool operandLike = (p.Kind is "word" or "quoted" or "number" or "string" && !(p.Kind == "word" && OperandBlock.Contains(p.Norm))) || (p.Kind == "punct" && p.Text == ")");
      if (operandLike && !(last.Kind == "word" && (OperandBlock.Contains(last.Norm) || last.Norm is "END" or "ASC" or "DESC"))) return expr.GetRange(0, expr.Count - 1);
    }
    return expr;
  }
  static string TokKey(Tok t) => t.Kind == "word" ? "w\0" + t.Norm.ToLowerInvariant() : t.Kind + "\0" + t.Norm;
  static bool SameSeq(List<Tok> a, List<Tok> b) { if (a.Count != b.Count) return false; for (int i = 0; i < a.Count; i++) if (TokKey(a[i]) != TokKey(b[i])) return false; return true; }

  // ------------------------------------------------------------------ types
  static readonly Regex IsoDate = new(@"^([0-9]{4})-([0-9]{2})-([0-9]{2})\z", RegexOptions.CultureInvariant);
  static readonly Regex Rfc3339 = new(@"^([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})\z", RegexOptions.CultureInvariant);
  static bool IsLeap(int y) => (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
  static readonly int[] Dim = { 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 };
  static bool ValidDate(int y, int mo, int d) => y >= 1 && y <= 9999 && mo >= 1 && mo <= 12 && d >= 1 && d <= Dim[mo - 1] + (mo == 2 && IsLeap(y) ? 1 : 0);
  static long DaysFromCivil(long y, int m, int d) {
    y -= m <= 2 ? 1 : 0;
    long era = (y >= 0 ? y : y - 399) / 400, yoe = y - era * 400;
    long doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1, doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + doe - 719468;
  }
  internal static double? ParseTemporal(object? v) {
    if (v is not string s) return null;
    var m = IsoDate.Match(s);
    if (m.Success) {
      int y = int.Parse(m.Groups[1].Value), mo = int.Parse(m.Groups[2].Value), d = int.Parse(m.Groups[3].Value);
      return ValidDate(y, mo, d) ? DaysFromCivil(y, mo, d) * 86400.0 : null;
    }
    m = Rfc3339.Match(s);
    if (m.Success) {
      int y = int.Parse(m.Groups[1].Value), mo = int.Parse(m.Groups[2].Value), d = int.Parse(m.Groups[3].Value);
      int h = int.Parse(m.Groups[4].Value), mi = int.Parse(m.Groups[5].Value), sec = int.Parse(m.Groups[6].Value);
      if (!ValidDate(y, mo, d) || h > 23 || mi > 59 || sec > 59) return null;
      double frac = m.Groups[7].Success ? double.Parse("0" + m.Groups[7].Value, NumberStyles.Float, CultureInfo.InvariantCulture) : 0.0;
      double off = 0; var tz = m.Groups[8].Value;
      if (tz != "Z" && tz != "z") {
        int sign = tz[0] == '+' ? 1 : -1, oh = int.Parse(tz.Substring(1, 2)), om = int.Parse(tz.Substring(4, 2));
        if (oh > 23 || om > 59) return null;
        off = sign * (oh * 3600 + om * 60);
      }
      double bse = DaysFromCivil(y, mo, d) * 86400.0 + h * 3600 + mi * 60 + sec;
      return bse - off + frac;
    }
    return null;
  }
  static bool IsNumericType(object v) => v is byte or sbyte or short or ushort or int or uint or long or ulong or float or double or decimal;
  static double ToDouble(object v) => v is decimal dm ? (double)dm : Convert.ToDouble(v, CultureInfo.InvariantCulture);
  static bool IsMissing(object? v) => v is null || v is string { Length: 0 } || (v is double d && !double.IsFinite(d)) || (v is float f && !float.IsFinite(f));
  static bool IsInt(object? v) => v is byte or sbyte or short or ushort or int or uint or long or ulong
    || (v is double d && double.IsFinite(d) && Math.Floor(d) == d) || (v is float f && float.IsFinite(f) && Math.Floor(f) == f) || (v is decimal m && decimal.Truncate(m) == m);
  static void CheckCell(object? v) {
    if (v is null or string or bool) return;
    if (v is long l) { if (l > 9007199254740991L || l < -9007199254740991L) throw new FeatureException("integer outside safe range"); return; }
    if (v is ulong ul) { if (ul > 9007199254740991UL) throw new FeatureException("integer outside safe range"); return; }
    if (IsNumericType(v)) {
      if (IsInt(v) && Math.Abs(ToDouble(v)) > SafeInt && v is not decimal) throw new FeatureException("integer outside safe range");
      if (v is decimal m && decimal.Truncate(m) == m && Math.Abs(m) > 9007199254740991m) throw new FeatureException("integer outside safe range");
      return;
    }
    throw new FeatureException(v is System.Collections.IEnumerable ? "nested values rejected" : $"unsupported cell type {v.GetType().Name}");
  }
  static string AsciiLower(string s) { var sb = new StringBuilder(s.Length); foreach (var ch in s) sb.Append(ch >= 'A' && ch <= 'Z' ? (char)(ch + 32) : ch); return sb.ToString(); }
  static bool IsNum(object? v) => v is not null && v is not bool && IsNumericType(v);

  static string ResolveType(string name, List<object?> values, string? explicitType) {
    var nm = values.Where(v => !IsMissing(v)).ToList();
    if (explicitType is not null) {
      if (Array.IndexOf(Contract.Types, explicitType) < 0) throw new FeatureException($"unknown explicit type '{explicitType}'");
      bool ok = explicitType switch {
        "nominal" => true,
        "quantitative" => nm.All(IsNum),
        "temporal" => nm.All(v => ParseTemporal(v) is not null),
        _ => nm.All(v => v is string || (v is not bool && IsInt(v))),
      };
      if (!ok) throw new FeatureException($"explicit type '{explicitType}' incompatible with column '{name}'");
      return explicitType;
    }
    if (nm.Count == 0) return "nominal";
    var ln = AsciiLower(name);
    if ((ln is "id" or "uuid" || ln.EndsWith("_id", StringComparison.Ordinal)) && nm.All(v => v is string || (v is not bool && IsInt(v)))) return "identifier";
    if (nm.All(v => ParseTemporal(v) is not null)) return "temporal";
    if (nm.All(IsNum)) return "quantitative";
    return "nominal";
  }

  sealed class Column {
    public string Name; public string Type; public int N, K; public List<string> Keys; public double[]? Num; public List<string> Strs;
    public Column(string name, List<object?> values, string? explicitType) {
      foreach (var v in values) CheckCell(v);
      Name = name; Type = ResolveType(name, values, explicitType);
      var nm = values.Where(v => !IsMissing(v)).ToList();
      N = nm.Count;
      Num = Type == "quantitative" ? nm.Select(v => { var d = ToDouble(v!); return d == 0 ? 0.0 : d; }).ToArray()
          : Type == "temporal" ? nm.Select(v => ParseTemporal(v)!.Value).ToArray() : null;
      Keys = nm.Select(v => Type == "temporal" ? "t:" + Fmt(ParseTemporal(v)!.Value)
          : v is bool b ? "b:" + (b ? "true" : "false")
          : IsNum(v) ? "n:" + Fmt(ToDouble(v!) == 0 ? 0.0 : ToDouble(v!)) : "s:" + v).ToList();
      K = Keys.Distinct(StringComparer.Ordinal).Count();
      Strs = nm.OfType<string>().ToList();
    }
  }
  static string Fmt(double d) => d.ToString("R", CultureInfo.InvariantCulture);

  static List<Column> ParseInput(IReadOnlyList<ColumnSpec> schema, IReadOnlyList<IReadOnlyList<object?>> rows) {
    int m = schema.Count;
    if (m == 0 || m > Contract.MaxColumns) throw new FeatureException("column count out of bounds");
    if (rows.Count > Contract.MaxRows) throw new FeatureException("row count out of bounds");
    foreach (var r in rows) if (r is null || r.Count != m) throw new FeatureException("ragged rows");
    return schema.Select((c, j) => new Column(c.Name, rows.Select(r => r[j]).ToList(), c.Type)).ToList();
  }

  // ------------------------------------------------------------------ SQL features
  static List<int> MatchName(Tok tok, List<Column> cols) {
    var res = new List<int>();
    if (tok.Kind == "word") { for (int j = 0; j < cols.Count; j++) if (AsciiLower(cols[j].Name) == AsciiLower(tok.Text)) res.Add(j); }
    else if (tok.Kind == "quoted") { for (int j = 0; j < cols.Count; j++) if (cols[j].Name == tok.Norm) res.Add(j); }
    return res;
  }
  static bool AscTemporal(List<Tok> term, List<Column> cols) {
    bool desc = false; var t = term;
    if (t.Count >= 2 && Kw(t[^1], "ASC", "DESC")) { desc = Kw(t[^1], "DESC"); t = t.GetRange(0, t.Count - 1); }
    if (t.Count != 1) return false;
    var tok = t[0]; List<int> cand;
    if (tok.Kind == "number" && AllDigits(tok.Text)) { long k = long.TryParse(tok.Text, out var p) ? p - 1 : -1; cand = k >= 0 && k < cols.Count ? new() { (int)k } : new(); }
    else cand = MatchName(tok, cols);
    return cand.Count == 1 && cols[cand[0]].Type == "temporal" && !desc;
  }
  static bool BinaryOps(List<Tok> expr) {
    for (int i = 0; i < expr.Count; i++) {
      var t = expr[i];
      if (Kw(t, "CASE") && i + 1 < expr.Count && Kw(expr[i + 1], "WHEN")) return true;
      if (t.Kind == "punct" && t.Text.Length == 1 && "+-*/".Contains(t.Text[0]) && i > 0) {
        var p = expr[i - 1];
        if (t.Text == "*" && p.Kind == "punct" && p.Text == ".") continue;
        bool operand = p.Kind is "number" or "string" or "quoted" || (p.Kind == "word" && !OperandBlock.Contains(p.Norm)) || (p.Kind == "punct" && p.Text == ")");
        if (operand) return true;
      }
    }
    return false;
  }
  static double CalcRatio(List<Tok> toks, int s) {
    var (a, b) = ProjectionSpan(toks, s); var exprs = SplitCommas(toks, a, b);
    return exprs.Count == 0 ? 0.0 : (double)exprs.Count(BinaryOps) / exprs.Count;
  }
  static List<List<Tok>> OuterProjection(List<Tok> toks, int s) { var (a, b) = ProjectionSpan(toks, s); return SplitCommas(toks, a, b).Select(ExprAndAlias).ToList(); }

  static double[] SqlFeatures(string sql, List<Column> cols) {
    var toks = Lex(sql); int n = toks.Count;
    var f = new double[16];
    f[0] = Math.Log(1 + n);
    f[1] = toks.Count(t => Kw(t, "JOIN"));
    int c2 = 0; for (int i = 1; i < n; i++) if (Kw(toks[i], "SELECT") && toks[i - 1].Kind == "punct" && toks[i - 1].Text == "(") c2++;
    f[2] = c2;
    var gb = new List<int>(); for (int i = 0; i < n - 1; i++) if (Kw(toks[i], "GROUP") && Kw(toks[i + 1], "BY")) gb.Add(i);
    f[3] = gb.Count > 0 ? 1 : 0;
    f[4] = gb.Sum(i => SplitCommas(toks, i + 2, ClauseEnd(toks, i + 2)).Count);
    var ob = new List<int>(); for (int i = 0; i < n - 1; i++) if (Kw(toks[i], "ORDER") && Kw(toks[i + 1], "BY")) ob.Add(i);
    f[5] = ob.Count > 0 ? 1 : 0;
    f[7] = toks.Any(t => Kw(t, "LIMIT", "TOP")) ? 1 : 0;
    f[8] = 1;
    var s = OuterSelect(toks);
    var (lo, hi) = s is int ss ? OuterRange(toks, ss) : (0, n);
    if (s is int sIdx) {
      int d0 = toks[sIdx].Depth;
      for (int i = lo; i < hi; i++) {
        var t = toks[i];
        if (t.Depth == d0 && Kw(t, "LIMIT", "TOP")) {
          var nxt = i + 1 < n ? toks[i + 1] : null;
          if (nxt is not null && nxt.Kind == "number" && AllDigits(nxt.Text)) f[8] = Math.Min(double.Parse(nxt.Text, CultureInfo.InvariantCulture), 1000.0) / 1000.0;
          break;
        }
      }
      foreach (var i in ob) {
        if (lo <= i && i < hi && toks[i].Depth == d0) {
          var terms = SplitCommas(toks, i + 2, ClauseEnd(toks, i + 2));
          if (terms.Count > 0) f[6] = AscTemporal(terms[0], cols) ? 1 : 0;
          break;
        }
      }
    }
    var inProj = new HashSet<int>();
    for (int i = 0; i < n; i++) if (Kw(toks[i], "SELECT")) { var (a, b) = ProjectionSpan(toks, i); for (int k = a; k < b; k++) inProj.Add(k); }
    f[9] = inProj.Count(i => Kw(toks[i], Agg) && FollowedByParen(toks, i));
    f[10] = Enumerable.Range(0, n).Any(i => Kw(toks[i], TemporalFn) && FollowedByParen(toks, i)) ? 1 : 0;
    f[11] = Enumerable.Range(0, n).Any(i => Kw(toks[i], "OVER") || (Kw(toks[i], "PARTITION") && i + 1 < n && Kw(toks[i + 1], "BY")) || (Kw(toks[i], "ROW_NUMBER", "LAG", "LEAD") && FollowedByParen(toks, i))) ? 1 : 0;
    f[12] = toks.Any(t => Kw(t, "HAVING")) ? 1 : 0;
    f[13] = toks.Any(t => Kw(t, "DISTINCT")) ? 1 : 0;
    f[14] = s is int s2 ? CalcRatio(toks, s2) : 0;
    int md = 0; foreach (var t in toks) md = Math.Max(md, t.Depth + (t.Kind == "punct" && t.Text == "(" ? 1 : 0));
    f[15] = md;
    return f;
  }

  // ------------------------------------------------------------------ global / column features
  static double EntropyNorm(Column c) {
    if (c.K <= 1) return 0;
    var order = new List<string>(); var cnt = new Dictionary<string, int>(StringComparer.Ordinal);
    foreach (var k in c.Keys) { if (!cnt.ContainsKey(k)) { cnt[k] = 0; order.Add(k); } cnt[k]++; }
    double h = 0; foreach (var k in order) { double p = (double)cnt[k] / c.N; h += p * Math.Log(p); }
    return -h / Math.Log(c.K);
  }
  static double[] GlobalFeatures(List<Column> cols, int N) {
    int M = cols.Count; int Count(string t) => cols.Count(c => c.Type == t);
    var nom = cols.Where(c => c.Type == "nominal").ToList();
    var f = new double[16];
    f[0] = Math.Log10(1 + N);
    f[1] = N == 1 ? 1 : 0; f[2] = N >= 2 && N <= 15 ? 1 : 0; f[3] = N > 50 ? 1 : 0;
    f[4] = M;
    f[5] = Count("temporal"); f[6] = Count("quantitative"); f[7] = Count("nominal"); f[8] = Count("identifier");
    f[9] = (double)Count("quantitative") / Math.Max(M, 1);
    f[10] = (double)Count("nominal") / Math.Max(M, 1);
    f[11] = (double)cols.Sum(c => c.N) / Math.Max(N * M, 1);
    double mx = 0; foreach (var c in nom) mx = Math.Max(mx, (double)c.K / Math.Max(N, 1));
    f[12] = mx;
    f[13] = nom.Count > 0 ? nom.Min(c => c.K) : 0;
    double crossed = 0;
    if (nom.Count == 2 && Count("quantitative") == 1 && N > 0 && cols.All(c => c.N == N)) {
      var pairs = new HashSet<string>(StringComparer.Ordinal);
      for (int i = 0; i < N; i++) pairs.Add(nom[0].Keys[i] + "\u0001" + nom[1].Keys[i]);
      if (pairs.Count == N && N == nom[0].K * nom[1].K) crossed = 1;
    }
    f[14] = crossed;
    if (nom.Count > 0) { double acc = 0; foreach (var c in nom) acc += EntropyNorm(c); f[15] = acc / nom.Count; }
    return f;
  }
  static double Quantile7(double[] s, double p) {
    int n = s.Length; double h = (n - 1) * p; int lo = (int)Math.Floor(h), hi = Math.Min(lo + 1, n - 1);
    return s[lo] + (h - lo) * (s[hi] - s[lo]);
  }
  static double[] Sorted(IEnumerable<double> a) { var r = a.ToArray(); Array.Sort(r); return r; }
  static int CodePoints(string s) { int k = 0; for (int i = 0; i < s.Length; i++) { if (char.IsHighSurrogate(s[i]) && i + 1 < s.Length && char.IsLowSurrogate(s[i + 1])) i++; k++; } return k; }

  static double[] GroupFlags(List<Tok> toks, List<Column> cols) {
    var flags = new double[cols.Count];
    if (OuterSelect(toks) is not int s) return flags;
    var (lo, hi) = OuterRange(toks, s); int d0 = toks[s].Depth;
    var proj = OuterProjection(toks, s); bool aligned = proj.Count == cols.Count;
    for (int i = lo; i < hi - 1; i++) {
      if (toks[i].Depth == d0 && Kw(toks[i], "GROUP") && Kw(toks[i + 1], "BY")) {
        foreach (var item in SplitCommas(toks, i + 2, ClauseEnd(toks, i + 2))) {
          var cand = new SortedSet<int>();
          if (item.Count == 1 && item[0].Kind == "number" && AllDigits(item[0].Text)) {
            long k = long.TryParse(item[0].Text, out var p) ? p - 1 : -1;
            if (k >= 0 && k < cols.Count) cand.Add((int)k);
          } else {
            if (item.Count == 1) foreach (var j in MatchName(item[0], cols)) cand.Add(j);
            if (aligned) for (int j = 0; j < proj.Count; j++) if (SameSeq(proj[j], item)) cand.Add(j);
          }
          if (cand.Count == 1) flags[cand.Min] = 1;
        }
      }
    }
    return flags;
  }
  static double[] AggFlags(List<Tok> toks, List<Column> cols) {
    var flags = new double[cols.Count];
    if (OuterSelect(toks) is not int s) return flags;
    var proj = OuterProjection(toks, s);
    if (proj.Count != cols.Count) return flags;
    for (int j = 0; j < proj.Count; j++) { var p = proj[j]; for (int k = 0; k < p.Count; k++) if (Kw(p[k], Agg) && k + 1 < p.Count && p[k + 1].Kind == "punct" && p[k + 1].Text == "(") { flags[j] = 1; break; } }
    return flags;
  }

  static double[][] ColumnFeatures(List<Column> cols, int N, double[] table, List<Tok> toks) {
    int M = cols.Count; var g = GroupFlags(toks, cols); var a = AggFlags(toks, cols);
    var outp = new double[M][];
    for (int j = 0; j < M; j++) {
      var c = cols[j]; var f = new double[28];
      f[0] = (double)j / Math.Max(M - 1, 1);
      f[1] = c.Type == "temporal" ? 1 : 0; f[2] = c.Type == "quantitative" ? 1 : 0; f[3] = c.Type == "nominal" ? 1 : 0; f[4] = c.Type == "identifier" ? 1 : 0;
      f[5] = g[j]; f[6] = a[j];
      f[7] = N > 0 ? 1 - (double)c.N / N : 0;
      f[8] = Math.Log10(1 + c.K);
      f[9] = (double)c.K / Math.Max(c.N, 1);
      f[10] = c.N > 0 && c.K == c.N ? 1 : 0;
      if (c.Strs.Count > 0) { long tot = 0; foreach (var s in c.Strs) tot += CodePoints(s); f[11] = ((double)tot / c.Strs.Count) / 50; }
      var x = c.Num;
      if (c.Type == "quantitative" && c.N > 0 && x is not null) {
        int n = c.N; double sum = 0; foreach (var v in x) sum += v;
        double mu = sum / n; double v2 = 0; foreach (var v in x) v2 += (v - mu) * (v - mu);
        double variance = v2 / n, sigma = Math.Sqrt(variance);
        f[12] = sigma / (Math.Abs(mu) + 1e-8);
        double mx = double.NegativeInfinity, mn = double.PositiveInfinity; foreach (var v in x) { if (v > mx) mx = v; if (v < mn) mn = v; }
        if (n >= 2 && mx != mn) {
          double a3 = 0, a4 = 0; foreach (var v in x) { double d = v - mu; a3 += d * d * d; a4 += (d * d) * (d * d); }
          f[13] = (a3 / n) / (sigma * sigma * sigma + 1e-8);
          f[14] = (a4 / n) / ((sigma * sigma) * (sigma * sigma) + 1e-8) - 3;
        }
        f[15] = (double)x.Count(v => v < 0) / n; f[16] = (double)x.Count(v => v == 0) / n;
        f[19] = (mx - mn) / (Math.Abs(mu) + 1e-8);
        var sx = Sorted(x); double med = Quantile7(sx, 0.5);
        f[20] = (Quantile7(sx, 0.75) - Quantile7(sx, 0.25)) / (Math.Abs(med) + 1e-8);
        f[21] = Quantile7(Sorted(x.Select(v => Math.Abs(v - med))), 0.5) / (Math.Abs(med) + 1e-8);
      }
      if ((c.Type == "quantitative" || c.Type == "temporal") && c.N >= 2 && x is not null) {
        int up = 0; for (int i = 0; i + 1 < x.Length; i++) if (x[i + 1] >= x[i]) up++;
        f[17] = (double)up / (c.N - 1);
      }
      if (c.Type == "temporal" && c.N >= 3 && x is not null) {
        var d = new double[x.Length - 1]; for (int i = 0; i + 1 < x.Length; i++) d[i] = x[i + 1] - x[i];
        double s1 = 0; foreach (var v in d) s1 += v; double md = s1 / d.Length;
        double s2 = 0; foreach (var v in d) s2 += (v - md) * (v - md);
        f[18] = (s2 / d.Length) / (md * md + 1e-8);
      }
      f[22] = table[3]; f[23] = table[6]; f[24] = table[10]; f[25] = table[16]; f[26] = table[21]; f[27] = table[22];
      outp[j] = f;
    }
    return outp;
  }

  static float[] Finalize(double[] vec, (string Name, double Lo, double Hi, double Default)[] defs) {
    var o = new float[vec.Length];
    for (int i = 0; i < vec.Length; i++) {
      double v = vec[i]; var (_, lo, hi, dflt) = defs[i];
      if (!double.IsFinite(v)) v = dflt;
      o[i] = (float)Math.Min(Math.Max(v, lo), hi);          // (float) rounds to nearest-even binary32
    }
    return o;
  }

  /// <summary>Compute the 32 table features and the M x 28 column features of SqlVizSpec-v1.0.0. SQL is never executed.</summary>
  public static Extracted Extract(string sql, IReadOnlyList<ColumnSpec> schema, IReadOnlyList<IReadOnlyList<object?>> rows) {
    var cols = ParseInput(schema, rows); int N = rows.Count; var toks = Lex(sql);
    var table = Finalize(SqlFeatures(sql, cols).Concat(GlobalFeatures(cols, N)).ToArray(), Contract.SqlFeatures.Concat(Contract.GlobalFeatures).ToArray());
    var colraw = ColumnFeatures(cols, N, table.Select(v => (double)v).ToArray(), toks);
    return new Extracted(table, colraw.Select(r => Finalize(r, Contract.ColumnFeatures)).ToArray());
  }
}
