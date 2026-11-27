"""Reference extractor for SqlVizSpec-v1.0.0 (frozen contract, spec/sqlvizspec-v1-features.json).

Pure-Python/binary64 implementation written from the contract text only (it does not reuse
any third-party feature-extraction code). Ambiguous contract readings are listed in
``research/kaggle/FEATURE_INTERPRETATIONS.md`` and must be confirmed by the contract owner
before cross-SDK parity is claimed.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

CONTRACT_VERSION = "SqlVizSpec-v1.0.0"
CONTRACT_SHA256 = "d14d140b9118c0b535d4e504af7f16546f47d56ac8f1692c2ab62615686e5864"
CONTRACT_PATH = Path(os.environ.get("SQLTOVIZ_CONTRACT") or Path(__file__).resolve().parents[3] / "spec" / "sqlvizspec-v1-features.json")
SAFE_INT = 2 ** 53 - 1
MAX_COLUMNS, MAX_ROWS = 128, 100_000


class FeatureError(ValueError):
    """Input rejected by the contract (malformed SQL lexing, bad types, out-of-bounds)."""


def load_contract(path: Path = CONTRACT_PATH, verify: bool = True) -> dict:
    raw = Path(path).read_bytes()
    if verify and hashlib.sha256(raw).hexdigest() != CONTRACT_SHA256:
        raise FeatureError("contract bytes do not match pinned SHA256")
    return json.loads(raw)


_CONTRACT = None


def contract() -> dict:
    global _CONTRACT
    if _CONTRACT is None:
        _CONTRACT = load_contract()
    return _CONTRACT


# ----------------------------------------------------------------------------- lexer
class Tok:
    __slots__ = ("kind", "text", "norm", "depth")

    def __init__(self, kind, text, norm, depth):
        self.kind, self.text, self.norm, self.depth = kind, text, norm, depth

    def __repr__(self):
        return f"{self.kind}:{self.text}"


_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*")
_NUM = re.compile(r"(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?")


def lex(sql: str) -> list:
    """Lexical analysis only. kinds: word (unquoted), quoted, string, number, punct."""
    toks, i, n, depth = [], 0, len(sql), 0
    while i < n:
        c = sql[i]
        if c.isspace():
            i += 1
        elif sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j < 0 else j + 1
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            if j < 0:
                raise FeatureError("unclosed block comment")
            i = j + 2
        elif c in ("'", '"', "`"):
            q, j, buf = c, i + 1, []
            while True:
                if j >= n:
                    raise FeatureError("unclosed quote")
                if sql[j] == q:
                    if j + 1 < n and sql[j + 1] == q:
                        buf.append(q)
                        j += 2
                        continue
                    break
                buf.append(sql[j])
                j += 1
            toks.append(Tok("string" if q == "'" else "quoted", sql[i:j + 1], "".join(buf), depth))
            i = j + 1
        elif c == "[":
            j = sql.find("]", i + 1)
            if j < 0:
                raise FeatureError("unclosed bracket identifier")
            toks.append(Tok("quoted", sql[i:j + 1], sql[i + 1:j], depth))
            i = j + 1
        else:
            m = _WORD.match(sql, i)
            if m:
                w = m.group()
                toks.append(Tok("word", w, w.upper(), depth))
                i = m.end()
                continue
            m = _NUM.match(sql, i)
            if m and (c.isdigit() or (c == "." and i + 1 < n and sql[i + 1].isdigit())):
                toks.append(Tok("number", m.group(), m.group(), depth))
                i = m.end()
                continue
            if c == "(":
                toks.append(Tok("punct", c, c, depth))
                depth += 1
            elif c == ")":
                depth = max(depth - 1, 0)
                toks.append(Tok("punct", c, c, depth))
            else:
                toks.append(Tok("punct", c, c, depth))
            i += 1
    return toks


def _kw(t, *names):
    return t.kind == "word" and t.norm in names


_CLAUSE_END = {"HAVING", "ORDER", "LIMIT", "OFFSET", "FETCH", "UNION", "INTERSECT", "EXCEPT", "WINDOW"}
_SETOPS = {"UNION", "INTERSECT", "EXCEPT"}
_AGG = {"SUM", "COUNT", "AVG", "MIN", "MAX"}
_TEMPORAL_FN = {"DATE_TRUNC", "EXTRACT", "YEAR", "MONTH", "DAY", "STRFTIME", "DATEPART"}
_OPERAND_BLOCK = {"SELECT", "AND", "OR", "NOT", "WHEN", "THEN", "ELSE", "CASE", "IN", "BETWEEN", "LIKE", "IS", "ON", "WHERE",
                  "BY", "HAVING", "DISTINCT", "ALL", "AS", "BEGIN", "EXISTS"}


def _followed_by_paren(toks, i):
    return i + 1 < len(toks) and toks[i + 1].kind == "punct" and toks[i + 1].text == "("


def _clause_end(toks, start):
    """Index (exclusive) where the clause starting at ``start`` ends (same depth boundaries)."""
    d = toks[start].depth if start < len(toks) else 0
    j = start
    while j < len(toks):
        t = toks[j]
        if t.depth < d or (t.kind == "punct" and t.text == ")" and t.depth < d):
            break
        if t.kind == "punct" and t.text == ";":
            break
        if t.depth == d and t.kind == "word" and t.norm in _CLAUSE_END:
            break
        j += 1
    return j


def _split_commas(toks, a, b):
    """Split toks[a:b] at commas of the minimum depth present in the span."""
    if a >= b:
        return []
    d = min(t.depth for t in toks[a:b])
    out, cur = [], []
    for t in toks[a:b]:
        if t.kind == "punct" and t.text == "," and t.depth == d:
            out.append(cur)
            cur = []
        else:
            cur.append(t)
    out.append(cur)
    return [e for e in out if e]


def _outer_select(toks):
    """Index of the first SELECT at minimum parenthesis depth (after any CTE bodies)."""
    sel = [i for i, t in enumerate(toks) if _kw(t, "SELECT")]
    if not sel:
        return None
    dmin = min(toks[i].depth for i in sel)
    for i in sel:
        if toks[i].depth == dmin:
            return i
    return None


def _projection_span(toks, s):
    """(start, end) of the projection after SELECT at index s: skips DISTINCT/ALL/TOP n."""
    a = s + 1
    d = toks[s].depth
    while a < len(toks) and toks[a].depth == d and (_kw(toks[a], "DISTINCT", "ALL")):
        a += 1
    if a + 1 < len(toks) and _kw(toks[a], "TOP") and toks[a + 1].kind == "number":
        a += 2
    b = a
    while b < len(toks):
        t = toks[b]
        if t.depth < d or (t.kind == "punct" and t.text == ";"):
            break
        if t.depth == d and _kw(t, "FROM", *_SETOPS):
            break
        b += 1
    return a, b


def _outer_range(toks, s):
    """Token range [s, end) of the outer (first) arm: ends at first depth-d set operator."""
    d = toks[s].depth
    for j in range(s + 1, len(toks)):
        if toks[j].depth < d:
            return s, j
        if toks[j].depth == d and _kw(toks[j], *_SETOPS):
            return s, j
    return s, len(toks)


def _expr_and_alias(expr):
    """Strip trailing alias (AS x | bare identifier after an operand) -> expression tokens, alias token|None."""
    if len(expr) >= 3 and _kw(expr[-2], "AS") and expr[-2].depth == expr[-1].depth and expr[-1].kind in ("word", "quoted", "string"):
        return expr[:-2], expr[-1]
    if len(expr) >= 2 and expr[-1].kind in ("word", "quoted") and expr[-1].depth == expr[0].depth:
        p = expr[-2]
        operand_like = p.kind in ("word", "quoted", "number", "string") and not (p.kind == "word" and p.norm in _OPERAND_BLOCK) \
            or (p.kind == "punct" and p.text == ")")
        if operand_like and not (expr[-1].kind == "word" and expr[-1].norm in _OPERAND_BLOCK | {"END", "ASC", "DESC"}):
            return expr[:-1], expr[-1]
    return expr, None


def _key(t):
    return ("w", t.norm.lower()) if t.kind == "word" else (t.kind, t.norm)


def _tokseq(ts):
    return [(_key(t)) if t.kind in ("word", "quoted") else (t.kind, t.norm) for t in ts]


# ------------------------------------------------------------------ type resolution
_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_RFC3339 = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2}):(\d{2})(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$")


def parse_temporal(v):
    """UTC seconds for ISO date-only or RFC3339-with-offset strings, else None."""
    if not isinstance(v, str):
        return None
    try:
        m = _ISO_DATE.match(v)
        if m:
            y, mo, d = map(int, m.groups())
            return float(datetime(y, mo, d, tzinfo=timezone.utc).timestamp())
        m = _RFC3339.match(v)
        if m:
            y, mo, d, h, mi, s = map(int, m.groups()[:6])
            frac = float(m.group(7)) if m.group(7) else 0.0
            tz = m.group(8)
            off = 0
            if tz not in ("Z", "z"):
                sign = 1 if tz[0] == "+" else -1
                oh, om = int(tz[1:3]), int(tz[4:6])
                if oh > 23 or om > 59:
                    return None
                off = sign * (oh * 3600 + om * 60)
            base = datetime(y, mo, d, h, mi, s, tzinfo=timezone.utc).timestamp()
            return float(base - off + frac)
    except (ValueError, OverflowError):
        return None
    return None


def is_missing(v) -> bool:
    if v is None:
        return True
    if isinstance(v, bool):
        return False
    if isinstance(v, float):
        return math.isnan(v) or math.isinf(v)
    if isinstance(v, str):
        return v == ""
    return False


def _check_cell(v):
    if isinstance(v, (list, dict, tuple, set)):
        raise FeatureError("nested values rejected")
    if isinstance(v, bool) or v is None or isinstance(v, str):
        return
    if isinstance(v, int):
        if abs(v) > SAFE_INT:
            raise FeatureError("integer outside safe range")
        return
    if isinstance(v, float):
        return
    raise FeatureError(f"unsupported cell type {type(v).__name__}")


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _ascii_lower(s: str) -> str:
    return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in s)


def resolve_type(name: str, values: list, explicit: str | None) -> str:
    nonmissing = [v for v in values if not is_missing(v)]
    types = contract()["canonical"]["types"]
    if explicit is not None:
        if explicit not in types:
            raise FeatureError(f"unknown explicit type {explicit!r}")
        ok = {
            "nominal": True,
            "quantitative": all(_is_num(v) for v in nonmissing),
            "temporal": all(parse_temporal(v) is not None for v in nonmissing),
            "identifier": all(isinstance(v, str) or (isinstance(v, int) and not isinstance(v, bool)) for v in nonmissing),
        }[explicit]
        if not ok:
            raise FeatureError(f"explicit type {explicit!r} incompatible with column {name!r}")
        return explicit
    if not nonmissing:
        return "nominal"
    ln = _ascii_lower(name)
    if (ln in ("id", "uuid") or ln.endswith("_id")) and all(
            isinstance(v, str) or (isinstance(v, int) and not isinstance(v, bool)) for v in nonmissing):
        return "identifier"
    if all(parse_temporal(v) is not None for v in nonmissing):
        return "temporal"
    if all(_is_num(v) for v in nonmissing):
        return "quantitative"
    return "nominal"


def _typed_key(v, ctype):
    if ctype == "temporal":
        return ("t", parse_temporal(v))
    if isinstance(v, bool):
        return ("b", v)
    if _is_num(v):
        x = float(v)
        return ("n", 0.0 if x == 0 else x)
    return ("s", v)


class Column:
    def __init__(self, name, values, explicit=None):
        for v in values:
            _check_cell(v)
        self.name = name
        self.values = list(values)
        self.type = resolve_type(name, self.values, explicit)
        self.mask = [is_missing(v) for v in self.values]
        nm = [v for v, m in zip(self.values, self.mask) if not m]
        self.n = len(nm)
        if self.type == "quantitative":
            self.num = [0.0 if float(v) == 0 else float(v) for v in nm]
        elif self.type == "temporal":
            self.num = [parse_temporal(v) for v in nm]
        else:
            self.num = None
        self.keys = [_typed_key(v, self.type) for v in nm]
        self.K = len(set(self.keys))
        self.strs = [v for v in nm if isinstance(v, str)]


def parse_input(schema: list, rows: list) -> list:
    """schema: [{name, type?}], rows: equal-length lists. Enforces contract bounds."""
    m = len(schema)
    if m == 0 or m > MAX_COLUMNS:
        raise FeatureError("column count out of bounds")
    if len(rows) > MAX_ROWS:
        raise FeatureError("row count out of bounds")
    for r in rows:
        if len(r) != m:
            raise FeatureError("ragged rows")
    return [Column(c["name"], [r[j] for r in rows], c.get("type")) for j, c in enumerate(schema)]


# ------------------------------------------------------------------ SQL features
def sql_features(sql: str, cols: list) -> list:
    toks = lex(sql)
    n = len(toks)
    names = [c.name for c in cols]
    f = [0.0] * 16
    f[0] = math.log(1 + n)
    f[1] = sum(1 for t in toks if _kw(t, "JOIN"))
    f[2] = sum(1 for i in range(1, n) if _kw(toks[i], "SELECT") and toks[i - 1].kind == "punct" and toks[i - 1].text == "(")
    gb = [i for i in range(n - 1) if _kw(toks[i], "GROUP") and _kw(toks[i + 1], "BY")]
    f[3] = 1.0 if gb else 0.0
    f[4] = float(sum(len(_split_commas(toks, i + 2, _clause_end(toks, i + 2))) for i in gb))
    ob = [i for i in range(n - 1) if _kw(toks[i], "ORDER") and _kw(toks[i + 1], "BY")]
    f[5] = 1.0 if ob else 0.0
    f[7] = 1.0 if any(_kw(t, "LIMIT", "TOP") for t in toks) else 0.0
    f[8] = 1.0
    s = _outer_select(toks)
    lo, hi = _outer_range(toks, s) if s is not None else (0, n)
    if s is not None:
        d0 = toks[s].depth
        # first outer LIMIT/TOP
        for i in range(lo, hi):
            t = toks[i]
            if t.depth == d0 and _kw(t, "LIMIT", "TOP"):
                nxt = toks[i + 1] if i + 1 < n else None
                if nxt is not None and nxt.kind == "number" and nxt.text.isdigit():
                    f[8] = min(int(nxt.text), 1000) / 1000.0
                break
        # ascending temporal order (first outer ORDER BY term)
        for i in ob:
            if lo <= i < hi and toks[i].depth == d0:
                end = _clause_end(toks, i + 2)
                terms = _split_commas(toks, i + 2, end)
                if terms:
                    f[6] = 1.0 if _asc_temporal(terms[0], cols) else 0.0
                break
    # aggregate count over union of projection spans of all SELECTs
    in_proj = set()
    for i, t in enumerate(toks):
        if _kw(t, "SELECT"):
            a, b = _projection_span(toks, i)
            in_proj.update(range(a, b))
    f[9] = float(sum(1 for i in in_proj if _kw(toks[i], *_AGG) and _followed_by_paren(toks, i)))
    f[10] = 1.0 if any(_kw(t, *_TEMPORAL_FN) and _followed_by_paren(toks, i) for i, t in enumerate(toks)) else 0.0
    f[11] = 1.0 if any(_kw(t, "OVER") or (_kw(t, "PARTITION") and i + 1 < n and _kw(toks[i + 1], "BY"))
                       or (_kw(t, "ROW_NUMBER", "LAG", "LEAD") and _followed_by_paren(toks, i)) for i, t in enumerate(toks)) else 0.0
    f[12] = 1.0 if any(_kw(t, "HAVING") for t in toks) else 0.0
    f[13] = 1.0 if any(_kw(t, "DISTINCT") for t in toks) else 0.0
    f[14] = _calc_ratio(toks, s) if s is not None else 0.0
    f[15] = float(max([t.depth + (1 if (t.kind == "punct" and t.text == "(") else 0) for t in toks] or [0]))
    return f


def _match_name(tok, cols):
    """Indexes of result columns matching identifier token (unquoted: ASCII case-insensitive; quoted: exact)."""
    if tok.kind == "word":
        return [j for j, c in enumerate(cols) if _ascii_lower(c.name) == _ascii_lower(tok.text)]
    if tok.kind == "quoted":
        return [j for j, c in enumerate(cols) if c.name == tok.norm]
    return []


def _asc_temporal(term, cols):
    desc = False
    t = list(term)
    if len(t) >= 2 and _kw(t[-1], "ASC", "DESC"):
        desc = _kw(t[-1], "DESC")
        t = t[:-1]
    if len(t) != 1:
        return False
    tok = t[0]
    if tok.kind == "number" and tok.text.isdigit():
        k = int(tok.text) - 1
        cand = [k] if 0 <= k < len(cols) else []
    else:
        cand = _match_name(tok, cols)
    return len(cand) == 1 and cols[cand[0]].type == "temporal" and not desc


def _binary_ops(expr):
    """True if expression contains a binary + - * / or CASE WHEN."""
    for i, t in enumerate(expr):
        if _kw(t, "CASE") and i + 1 < len(expr) and _kw(expr[i + 1], "WHEN"):
            return True
        if t.kind == "punct" and t.text in "+-*/" and i > 0:
            p = expr[i - 1]
            if t.text == "*" and p.kind == "punct" and p.text == ".":
                continue  # t.* wildcard
            operand = p.kind in ("number", "string", "quoted") or (p.kind == "word" and p.norm not in _OPERAND_BLOCK) \
                or (p.kind == "punct" and p.text == ")")
            if operand:
                return True
    return False


def _calc_ratio(toks, s):
    a, b = _projection_span(toks, s)
    exprs = _split_commas(toks, a, b)
    if not exprs:
        return 0.0
    return sum(1 for e in exprs if _binary_ops(e)) / len(exprs)


def outer_projection(toks, s):
    a, b = _projection_span(toks, s)
    return [_expr_and_alias(e)[0] for e in _split_commas(toks, a, b)]


def _group_flags(toks, cols):
    flags = [0.0] * len(cols)
    s = _outer_select(toks)
    if s is None:
        return flags
    lo, hi = _outer_range(toks, s)
    d0 = toks[s].depth
    proj = outer_projection(toks, s)
    aligned = len(proj) == len(cols)
    for i in range(lo, hi - 1):
        if toks[i].depth == d0 and _kw(toks[i], "GROUP") and _kw(toks[i + 1], "BY"):
            for item in _split_commas(toks, i + 2, _clause_end(toks, i + 2)):
                cand = set()
                if len(item) == 1 and item[0].kind == "number" and item[0].text.isdigit():
                    k = int(item[0].text) - 1
                    if 0 <= k < len(cols):
                        cand.add(k)
                else:
                    if len(item) == 1:
                        cand.update(_match_name(item[0], cols))
                    if aligned:
                        seq = _tokseq(item)
                        cand.update(j for j, p in enumerate(proj) if _tokseq(p) == seq)
                if len(cand) == 1:
                    flags[next(iter(cand))] = 1.0
    return flags


def _agg_flags(toks, cols):
    s = _outer_select(toks)
    flags = [0.0] * len(cols)
    if s is None:
        return flags
    proj = outer_projection(toks, s)
    if len(proj) != len(cols):
        return flags
    for j, p in enumerate(proj):
        if any(_kw(t, *_AGG) and k + 1 < len(p) and p[k + 1].kind == "punct" and p[k + 1].text == "(" for k, t in enumerate(p)):
            flags[j] = 1.0
    return flags


# ------------------------------------------------------------------ global / column features
def _entropy_norm(c):
    if c.K <= 1:
        return 0.0
    cnt = Counter(c.keys)
    h = -sum((v / c.n) * math.log(v / c.n) for v in cnt.values())
    return h / math.log(c.K)


def global_features(cols: list, N: int) -> list:
    M = len(cols)
    typ = Counter(c.type for c in cols)
    nom = [c for c in cols if c.type == "nominal"]
    f = [0.0] * 16
    f[0] = math.log10(1 + N)
    f[1] = 1.0 if N == 1 else 0.0
    f[2] = 1.0 if 2 <= N <= 15 else 0.0
    f[3] = 1.0 if N > 50 else 0.0
    f[4] = float(M)
    f[5], f[6], f[7], f[8] = (float(typ[t]) for t in ("temporal", "quantitative", "nominal", "identifier"))
    f[9] = typ["quantitative"] / max(M, 1)
    f[10] = typ["nominal"] / max(M, 1)
    f[11] = sum(c.n for c in cols) / max(N * M, 1)
    f[12] = max((c.K / max(N, 1) for c in nom), default=0.0)
    f[13] = float(min((c.K for c in nom), default=0))
    crossed = 0.0
    if len(nom) == 2 and typ["quantitative"] == 1 and N > 0 and all(c.n == N for c in cols):
        pairs = list(zip(nom[0].keys, nom[1].keys))
        if len(set(pairs)) == N and N == nom[0].K * nom[1].K:
            crossed = 1.0
    f[14] = crossed
    f[15] = sum(_entropy_norm(c) for c in nom) / len(nom) if nom else 0.0
    return f


def _quantile7(sorted_x, p):
    n = len(sorted_x)
    h = (n - 1) * p
    lo = math.floor(h)
    hi = min(lo + 1, n - 1)
    return sorted_x[lo] + (h - lo) * (sorted_x[hi] - sorted_x[lo])


def _median(sorted_x):
    return _quantile7(sorted_x, 0.5)


def column_features(cols: list, N: int, table: list, sql_toks) -> list:
    M = len(cols)
    gflag = _group_flags(sql_toks, cols) if sql_toks is not None else [0.0] * M
    aflag = _agg_flags(sql_toks, cols) if sql_toks is not None else [0.0] * M
    out = []
    for j, c in enumerate(cols):
        f = [0.0] * 28
        f[0] = j / max(M - 1, 1)
        f[1], f[2], f[3], f[4] = (1.0 if c.type == t else 0.0 for t in ("temporal", "quantitative", "nominal", "identifier"))
        f[5], f[6] = gflag[j], aflag[j]
        f[7] = 1 - c.n / N if N > 0 else 0.0
        f[8] = math.log10(1 + c.K)
        f[9] = c.K / max(c.n, 1)
        f[10] = 1.0 if (c.n > 0 and c.K == c.n) else 0.0
        f[11] = (sum(len(s) for s in c.strs) / len(c.strs)) / 50 if c.strs else 0.0
        x = c.num
        if c.type == "quantitative" and c.n > 0:
            n = c.n
            mu = sum(x) / n
            var = sum((v - mu) ** 2 for v in x) / n
            sigma = math.sqrt(var)
            f[12] = sigma / (abs(mu) + 1e-8)
            if n >= 2 and var > 0:
                m3 = sum((v - mu) ** 3 for v in x) / n
                m4 = sum((v - mu) ** 4 for v in x) / n
                f[13] = m3 / (sigma ** 3 + 1e-8)
                f[14] = m4 / (sigma ** 4 + 1e-8) - 3
            f[15] = sum(1 for v in x if v < 0) / n
            f[16] = sum(1 for v in x if v == 0) / n
            f[19] = (max(x) - min(x)) / (abs(mu) + 1e-8)
            sx = sorted(x)
            med = _median(sx)
            f[20] = (_quantile7(sx, 0.75) - _quantile7(sx, 0.25)) / (abs(med) + 1e-8)
            f[21] = _median(sorted(abs(v - med) for v in x)) / (abs(med) + 1e-8)
        if c.type in ("quantitative", "temporal") and c.n >= 2:
            f[17] = sum(1 for a, b in zip(x, x[1:]) if b >= a) / (c.n - 1)
        if c.type == "temporal" and c.n >= 3:
            d = [b - a for a, b in zip(x, x[1:])]
            md = sum(d) / len(d)
            f[18] = (sum((v - md) ** 2 for v in d) / len(d)) / (abs(md) ** 2 + 1e-8)
        f[22], f[23], f[24] = table[3], table[6], table[10]
        f[25], f[26], f[27] = table[16], table[21], table[22]
        out.append(f)
    return out


def _finalize(vec, defs):
    res = []
    for v, d in zip(vec, defs):
        lo, hi = d["range"]
        v = float(v)
        if not math.isfinite(v):
            v = float(d["default"])
        v = min(max(v, lo), hi)
        res.append(v)
    return np.asarray(res, dtype=np.float32)


def extract(sql: str, schema: list, rows: list) -> tuple:
    """Return (table_features[32] float32, column_features[M,28] float32) for SQL + result set."""
    C = contract()
    cols = parse_input(schema, rows)
    N = len(rows)
    toks = lex(sql)
    sqlf = sql_features(sql, cols)
    glob = global_features(cols, N)
    table_raw = sqlf + glob
    sdefs = C["sql_features"] + C["global_features"]
    table = _finalize(table_raw, sdefs)
    colraw = column_features(cols, N, [float(v) for v in table], toks)
    cdefs = C["column_features"]
    colmat = np.stack([_finalize(r, cdefs) for r in colraw]).astype(np.float32)
    return table, colmat


def interpretations_pin(repo: str | Path | None = None) -> dict:
    """Pin of the normative interpretation document (confirmed by the contract owner): file SHA256 + last commit."""
    import subprocess
    repo = Path(repo) if repo else Path(__file__).resolve().parents[3]
    doc = repo / "research" / "kaggle" / "FEATURE_INTERPRETATIONS.md"
    sha = hashlib.sha256(doc.read_bytes()).hexdigest()
    r = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%H", "--", "research/kaggle/FEATURE_INTERPRETATIONS.md"],
                       capture_output=True, text=True)
    return {"file": "research/kaggle/FEATURE_INTERPRETATIONS.md", "sha256": sha, "last_commit": r.stdout.strip() or None,
            "status": "confirmed normative clarification of SqlVizSpec-v1.0.0 (E02, issues #2 #3 #36)"}
