// SqlVizSpec-v1.0.0 feature engine (zero dependencies). Port of the Python/reference implementation; behaviour is pinned by
// parity/golden_v1.json and the nine confirmed interpretations (research/kaggle/FEATURE_INTERPRETATIONS.md).
import { COLUMN_FEATURES, GLOBAL_FEATURES, MAX_COLUMNS, MAX_ROWS, SQL_FEATURES, TYPES } from "./contract.js";
export class FeatureError extends Error {
    constructor(m) { super(m); this.name = "FeatureError"; }
}
const SAFE_INT = Number.MAX_SAFE_INTEGER;
const WORD = /[A-Za-z_][A-Za-z0-9_$]*/y;
const NUM = /(?:[0-9]+\.[0-9]*|\.[0-9]+|[0-9]+)(?:[eE][+-]?[0-9]+)?/y;
const DIGITS = "0123456789";
const allDigits = (s) => s.length > 0 && [...s].every((ch) => DIGITS.includes(ch));
// Unicode White_Space as defined by the contract port (identical to Python str.isspace)
const isSpace = (cp) => (cp >= 0x09 && cp <= 0x0d) || (cp >= 0x1c && cp <= 0x20) || cp === 0x85 || cp === 0xa0 || cp === 0x1680 ||
    (cp >= 0x2000 && cp <= 0x200a) || cp === 0x2028 || cp === 0x2029 || cp === 0x202f || cp === 0x205f || cp === 0x3000;
export function lex(sql) {
    const toks = [];
    let i = 0, depth = 0;
    const n = sql.length;
    while (i < n) {
        const cp = sql.codePointAt(i);
        const c = String.fromCodePoint(cp);
        if (isSpace(cp)) {
            i += c.length;
            continue;
        }
        if (sql.startsWith("--", i)) {
            const j = sql.indexOf("\n", i);
            i = j < 0 ? n : j + 1;
            continue;
        }
        if (sql.startsWith("/*", i)) {
            const j = sql.indexOf("*/", i + 2);
            if (j < 0)
                throw new FeatureError("unclosed block comment");
            i = j + 2;
            continue;
        }
        if (c === "'" || c === '"' || c === "`") {
            let j = i + 1;
            let buf = "";
            for (;;) {
                if (j >= n)
                    throw new FeatureError("unclosed quote");
                if (sql[j] === c) {
                    if (j + 1 < n && sql[j + 1] === c) {
                        buf += c;
                        j += 2;
                        continue;
                    }
                    break;
                }
                buf += sql[j];
                j += 1;
            }
            toks.push({ kind: c === "'" ? "string" : "quoted", text: sql.slice(i, j + 1), norm: buf, depth });
            i = j + 1;
            continue;
        }
        if (c === "[") {
            const j = sql.indexOf("]", i + 1);
            if (j < 0)
                throw new FeatureError("unclosed bracket identifier");
            toks.push({ kind: "quoted", text: sql.slice(i, j + 1), norm: sql.slice(i + 1, j), depth });
            i = j + 1;
            continue;
        }
        WORD.lastIndex = i;
        let m = WORD.exec(sql);
        if (m) {
            toks.push({ kind: "word", text: m[0], norm: m[0].toUpperCase(), depth });
            i += m[0].length;
            continue;
        }
        NUM.lastIndex = i;
        m = NUM.exec(sql);
        if (m && (DIGITS.includes(c) || (c === "." && i + 1 < n && DIGITS.includes(sql[i + 1])))) {
            toks.push({ kind: "number", text: m[0], norm: m[0], depth });
            i += m[0].length;
            continue;
        }
        if (c === "(") {
            toks.push({ kind: "punct", text: c, norm: c, depth });
            depth += 1;
        }
        else if (c === ")") {
            depth = Math.max(depth - 1, 0);
            toks.push({ kind: "punct", text: c, norm: c, depth });
        }
        else
            toks.push({ kind: "punct", text: c, norm: c, depth });
        i += c.length;
    }
    return toks;
}
const kw = (t, ...names) => t.kind === "word" && names.includes(t.norm);
const CLAUSE_END = new Set(["HAVING", "ORDER", "LIMIT", "OFFSET", "FETCH", "UNION", "INTERSECT", "EXCEPT", "WINDOW"]);
const SETOPS = ["UNION", "INTERSECT", "EXCEPT"];
const AGG = ["SUM", "COUNT", "AVG", "MIN", "MAX"];
const TEMPORAL_FN = ["DATE_TRUNC", "EXTRACT", "YEAR", "MONTH", "DAY", "STRFTIME", "DATEPART"];
const OPERAND_BLOCK = new Set(["SELECT", "AND", "OR", "NOT", "WHEN", "THEN", "ELSE", "CASE", "IN", "BETWEEN", "LIKE", "IS", "ON", "WHERE", "BY", "HAVING", "DISTINCT", "ALL", "AS", "BEGIN", "EXISTS"]);
const followedByParen = (toks, i) => i + 1 < toks.length && toks[i + 1].kind === "punct" && toks[i + 1].text === "(";
function clauseEnd(toks, start) {
    const d = start < toks.length ? toks[start].depth : 0;
    let j = start;
    while (j < toks.length) {
        const t = toks[j];
        if (t.depth < d || (t.kind === "punct" && t.text === ")" && t.depth < d))
            break;
        if (t.kind === "punct" && t.text === ";")
            break;
        if (t.depth === d && t.kind === "word" && CLAUSE_END.has(t.norm))
            break;
        j += 1;
    }
    return j;
}
function splitCommas(toks, a, b) {
    if (a >= b)
        return [];
    let d = Infinity;
    for (let k = a; k < b; k++)
        if (toks[k].depth < d)
            d = toks[k].depth;
    const out = [];
    let cur = [];
    for (let k = a; k < b; k++) {
        const t = toks[k];
        if (t.kind === "punct" && t.text === "," && t.depth === d) {
            out.push(cur);
            cur = [];
        }
        else
            cur.push(t);
    }
    out.push(cur);
    return out.filter((e) => e.length > 0);
}
function outerSelect(toks) {
    const sel = [];
    toks.forEach((t, i) => { if (kw(t, "SELECT"))
        sel.push(i); });
    if (!sel.length)
        return null;
    let dmin = Infinity;
    for (const i of sel)
        if (toks[i].depth < dmin)
            dmin = toks[i].depth;
    for (const i of sel)
        if (toks[i].depth === dmin)
            return i;
    return null;
}
function projectionSpan(toks, s) {
    let a = s + 1;
    const d = toks[s].depth;
    while (a < toks.length && toks[a].depth === d && kw(toks[a], "DISTINCT", "ALL"))
        a += 1;
    if (a + 1 < toks.length && kw(toks[a], "TOP") && toks[a + 1].kind === "number")
        a += 2;
    let b = a;
    while (b < toks.length) {
        const t = toks[b];
        if (t.depth < d || (t.kind === "punct" && t.text === ";"))
            break;
        if (t.depth === d && kw(t, "FROM", ...SETOPS))
            break;
        b += 1;
    }
    return [a, b];
}
function outerRange(toks, s) {
    const d = toks[s].depth;
    for (let j = s + 1; j < toks.length; j++) {
        if (toks[j].depth < d)
            return [s, j];
        if (toks[j].depth === d && kw(toks[j], ...SETOPS))
            return [s, j];
    }
    return [s, toks.length];
}
function exprAndAlias(expr) {
    const last = expr[expr.length - 1];
    if (expr.length >= 3 && kw(expr[expr.length - 2], "AS") && expr[expr.length - 2].depth === last.depth && (last.kind === "word" || last.kind === "quoted" || last.kind === "string"))
        return expr.slice(0, -2);
    if (expr.length >= 2 && (last.kind === "word" || last.kind === "quoted") && last.depth === expr[0].depth) {
        const p = expr[expr.length - 2];
        const operandLike = ((p.kind === "word" || p.kind === "quoted" || p.kind === "number" || p.kind === "string") && !(p.kind === "word" && OPERAND_BLOCK.has(p.norm))) ||
            (p.kind === "punct" && p.text === ")");
        if (operandLike && !(last.kind === "word" && (OPERAND_BLOCK.has(last.norm) || ["END", "ASC", "DESC"].includes(last.norm))))
            return expr.slice(0, -1);
    }
    return expr;
}
const tokKey = (t) => (t.kind === "word" ? "w\u0000" + t.norm.toLowerCase() : t.kind + "\u0000" + t.norm);
const sameSeq = (a, b) => a.length === b.length && a.every((t, i) => tokKey(t) === tokKey(b[i]));
// ------------------------------------------------------------------ types
const ISO_DATE = /^([0-9]{4})-([0-9]{2})-([0-9]{2})$/;
const RFC3339 = /^([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})$/;
const isLeap = (y) => (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
const DIM = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
function daysFromCivil(y, m, d) {
    y -= m <= 2 ? 1 : 0;
    const era = Math.floor(y / 400), yoe = y - era * 400;
    const doy = Math.floor((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5) + d - 1;
    const doe = yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy;
    return era * 146097 + doe - 719468;
}
const validDate = (y, mo, d) => y >= 1 && y <= 9999 && mo >= 1 && mo <= 12 && d >= 1 && d <= DIM[mo - 1] + (mo === 2 && isLeap(y) ? 1 : 0);
export function parseTemporal(v) {
    if (typeof v !== "string")
        return null;
    let m = ISO_DATE.exec(v);
    if (m) {
        const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
        return validDate(y, mo, d) ? daysFromCivil(y, mo, d) * 86400 : null;
    }
    m = RFC3339.exec(v);
    if (m) {
        const [y, mo, d, h, mi, s] = [1, 2, 3, 4, 5, 6].map((k) => Number(m[k]));
        if (!validDate(y, mo, d) || h > 23 || mi > 59 || s > 59)
            return null;
        const frac = m[7] ? parseFloat(m[7]) : 0;
        let off = 0;
        const tz = m[8];
        if (tz !== "Z" && tz !== "z") {
            const sign = tz[0] === "+" ? 1 : -1;
            const oh = Number(tz.slice(1, 3)), om = Number(tz.slice(4, 6));
            if (oh > 23 || om > 59)
                return null;
            off = sign * (oh * 3600 + om * 60);
        }
        const base = daysFromCivil(y, mo, d) * 86400 + h * 3600 + mi * 60 + s;
        return base - off + frac;
    }
    return null;
}
export const isMissing = (v) => v === null || v === undefined || (typeof v === "number" && !Number.isFinite(v)) || v === "";
function checkCell(v) {
    if (v === null || v === undefined || typeof v === "string" || typeof v === "boolean")
        return;
    if (typeof v === "number") {
        if (Number.isFinite(v) && Number.isInteger(v) && Math.abs(v) > SAFE_INT)
            throw new FeatureError("integer outside safe range");
        return;
    }
    if (typeof v === "bigint") {
        if (v > BigInt(SAFE_INT) || v < -BigInt(SAFE_INT))
            throw new FeatureError("integer outside safe range");
        return;
    }
    if (typeof v === "object")
        throw new FeatureError("nested values rejected");
    throw new FeatureError(`unsupported cell type ${typeof v}`);
}
const isInt = (v) => (typeof v === "number" && Number.isFinite(v) && Number.isInteger(v)) || typeof v === "bigint";
const isNum = (v) => typeof v === "number" || typeof v === "bigint";
const asciiLower = (s) => s.replace(/[A-Z]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) + 32));
function resolveType(name, values, explicit) {
    const nm = values.filter((v) => !isMissing(v));
    if (explicit !== undefined) {
        if (!TYPES.includes(explicit))
            throw new FeatureError(`unknown explicit type '${explicit}'`);
        const ok = explicit === "nominal" ? true : explicit === "quantitative" ? nm.every(isNum) : explicit === "temporal" ? nm.every((v) => parseTemporal(v) !== null)
            : nm.every((v) => typeof v === "string" || isInt(v));
        if (!ok)
            throw new FeatureError(`explicit type '${explicit}' incompatible with column '${name}'`);
        return explicit;
    }
    if (!nm.length)
        return "nominal";
    const ln = asciiLower(name);
    if ((ln === "id" || ln === "uuid" || ln.endsWith("_id")) && nm.every((v) => typeof v === "string" || isInt(v)))
        return "identifier";
    if (nm.every((v) => parseTemporal(v) !== null))
        return "temporal";
    if (nm.every(isNum))
        return "quantitative";
    return "nominal";
}
class Column {
    name;
    type;
    n;
    K;
    keys;
    num;
    strs;
    constructor(name, values, explicit) {
        values.forEach(checkCell);
        this.name = name;
        this.type = resolveType(name, values, explicit);
        const nm = values.filter((v) => !isMissing(v));
        this.n = nm.length;
        this.num = this.type === "quantitative" ? nm.map((v) => (Number(v) === 0 ? 0 : Number(v))) : this.type === "temporal" ? nm.map((v) => parseTemporal(v)) : null;
        this.keys = nm.map((v) => this.type === "temporal" ? "t:" + String(parseTemporal(v)) : typeof v === "boolean" ? "b:" + v : isNum(v) ? "n:" + String(Number(v) === 0 ? 0 : Number(v)) : "s:" + v);
        this.K = new Set(this.keys).size;
        this.strs = nm.filter((v) => typeof v === "string");
    }
}
function parseInput(schema, rows) {
    const m = schema.length;
    if (m === 0 || m > MAX_COLUMNS)
        throw new FeatureError("column count out of bounds");
    if (rows.length > MAX_ROWS)
        throw new FeatureError("row count out of bounds");
    for (const r of rows)
        if (!Array.isArray(r) || r.length !== m)
            throw new FeatureError("ragged rows");
    return schema.map((c, j) => new Column(c.name, rows.map((r) => r[j]), c.type));
}
// ------------------------------------------------------------------ SQL features
const ascTemporal = (term, cols) => {
    let desc = false, t = term;
    if (t.length >= 2 && kw(t[t.length - 1], "ASC", "DESC")) {
        desc = kw(t[t.length - 1], "DESC");
        t = t.slice(0, -1);
    }
    if (t.length !== 1)
        return false;
    const tok = t[0];
    let cand;
    if (tok.kind === "number" && allDigits(tok.text)) {
        const k = Number(tok.text) - 1;
        cand = k >= 0 && k < cols.length ? [k] : [];
    }
    else
        cand = matchName(tok, cols);
    return cand.length === 1 && cols[cand[0]].type === "temporal" && !desc;
};
function matchName(tok, cols) {
    const out = [];
    if (tok.kind === "word")
        cols.forEach((c, j) => { if (asciiLower(c.name) === asciiLower(tok.text))
            out.push(j); });
    else if (tok.kind === "quoted")
        cols.forEach((c, j) => { if (c.name === tok.norm)
            out.push(j); });
    return out;
}
function binaryOps(expr) {
    for (let i = 0; i < expr.length; i++) {
        const t = expr[i];
        if (kw(t, "CASE") && i + 1 < expr.length && kw(expr[i + 1], "WHEN"))
            return true;
        if (t.kind === "punct" && t.text.length === 1 && "+-*/".includes(t.text) && i > 0) {
            const p = expr[i - 1];
            if (t.text === "*" && p.kind === "punct" && p.text === ".")
                continue;
            const operand = p.kind === "number" || p.kind === "string" || p.kind === "quoted" || (p.kind === "word" && !OPERAND_BLOCK.has(p.norm)) || (p.kind === "punct" && p.text === ")");
            if (operand)
                return true;
        }
    }
    return false;
}
function calcRatio(toks, s) {
    const [a, b] = projectionSpan(toks, s);
    const exprs = splitCommas(toks, a, b);
    return exprs.length ? exprs.filter(binaryOps).length / exprs.length : 0;
}
const outerProjection = (toks, s) => { const [a, b] = projectionSpan(toks, s); return splitCommas(toks, a, b).map(exprAndAlias); };
function sqlFeatures(sql, cols) {
    const toks = lex(sql), n = toks.length;
    const f = new Array(16).fill(0);
    f[0] = Math.log(1 + n);
    f[1] = toks.filter((t) => kw(t, "JOIN")).length;
    let c2 = 0;
    for (let i = 1; i < n; i++)
        if (kw(toks[i], "SELECT") && toks[i - 1].kind === "punct" && toks[i - 1].text === "(")
            c2++;
    f[2] = c2;
    const gb = [];
    for (let i = 0; i < n - 1; i++)
        if (kw(toks[i], "GROUP") && kw(toks[i + 1], "BY"))
            gb.push(i);
    f[3] = gb.length ? 1 : 0;
    f[4] = gb.reduce((acc, i) => acc + splitCommas(toks, i + 2, clauseEnd(toks, i + 2)).length, 0);
    const ob = [];
    for (let i = 0; i < n - 1; i++)
        if (kw(toks[i], "ORDER") && kw(toks[i + 1], "BY"))
            ob.push(i);
    f[5] = ob.length ? 1 : 0;
    f[7] = toks.some((t) => kw(t, "LIMIT", "TOP")) ? 1 : 0;
    f[8] = 1;
    const s = outerSelect(toks);
    const [lo, hi] = s !== null ? outerRange(toks, s) : [0, n];
    if (s !== null) {
        const d0 = toks[s].depth;
        for (let i = lo; i < hi; i++) {
            const t = toks[i];
            if (t.depth === d0 && kw(t, "LIMIT", "TOP")) {
                const nxt = i + 1 < n ? toks[i + 1] : null;
                if (nxt && nxt.kind === "number" && allDigits(nxt.text))
                    f[8] = Math.min(Number(nxt.text), 1000) / 1000;
                break;
            }
        }
        for (const i of ob) {
            if (lo <= i && i < hi && toks[i].depth === d0) {
                const terms = splitCommas(toks, i + 2, clauseEnd(toks, i + 2));
                if (terms.length)
                    f[6] = ascTemporal(terms[0], cols) ? 1 : 0;
                break;
            }
        }
    }
    const inProj = new Set();
    toks.forEach((t, i) => { if (kw(t, "SELECT")) {
        const [a, b] = projectionSpan(toks, i);
        for (let k = a; k < b; k++)
            inProj.add(k);
    } });
    let agg = 0;
    for (const i of inProj)
        if (kw(toks[i], ...AGG) && followedByParen(toks, i))
            agg++;
    f[9] = agg;
    f[10] = toks.some((t, i) => kw(t, ...TEMPORAL_FN) && followedByParen(toks, i)) ? 1 : 0;
    f[11] = toks.some((t, i) => kw(t, "OVER") || (kw(t, "PARTITION") && i + 1 < n && kw(toks[i + 1], "BY")) || (kw(t, "ROW_NUMBER", "LAG", "LEAD") && followedByParen(toks, i))) ? 1 : 0;
    f[12] = toks.some((t) => kw(t, "HAVING")) ? 1 : 0;
    f[13] = toks.some((t) => kw(t, "DISTINCT")) ? 1 : 0;
    f[14] = s !== null ? calcRatio(toks, s) : 0;
    let md = 0;
    for (const t of toks)
        md = Math.max(md, t.depth + (t.kind === "punct" && t.text === "(" ? 1 : 0));
    f[15] = md;
    return f;
}
// ------------------------------------------------------------------ global / column features
function entropyNorm(c) {
    if (c.K <= 1)
        return 0;
    const cnt = new Map();
    for (const k of c.keys)
        cnt.set(k, (cnt.get(k) ?? 0) + 1);
    let h = 0;
    for (const v of cnt.values())
        h += (v / c.n) * Math.log(v / c.n);
    return -h / Math.log(c.K);
}
function globalFeatures(cols, N) {
    const M = cols.length;
    const typ = { temporal: 0, quantitative: 0, nominal: 0, identifier: 0 };
    for (const c of cols)
        typ[c.type]++;
    const nom = cols.filter((c) => c.type === "nominal");
    const f = new Array(16).fill(0);
    f[0] = Math.log10(1 + N);
    f[1] = N === 1 ? 1 : 0;
    f[2] = N >= 2 && N <= 15 ? 1 : 0;
    f[3] = N > 50 ? 1 : 0;
    f[4] = M;
    f[5] = typ.temporal;
    f[6] = typ.quantitative;
    f[7] = typ.nominal;
    f[8] = typ.identifier;
    f[9] = typ.quantitative / Math.max(M, 1);
    f[10] = typ.nominal / Math.max(M, 1);
    f[11] = cols.reduce((a, c) => a + c.n, 0) / Math.max(N * M, 1);
    f[12] = nom.reduce((a, c) => Math.max(a, c.K / Math.max(N, 1)), 0);
    f[13] = nom.length ? Math.min(...nom.map((c) => c.K)) : 0;
    let crossed = 0;
    if (nom.length === 2 && typ.quantitative === 1 && N > 0 && cols.every((c) => c.n === N)) {
        const pairs = new Set();
        for (let i = 0; i < N; i++)
            pairs.add(nom[0].keys[i] + "\u0001" + nom[1].keys[i]);
        if (pairs.size === N && N === nom[0].K * nom[1].K)
            crossed = 1;
    }
    f[14] = crossed;
    if (nom.length) {
        let acc = 0;
        for (const c of nom)
            acc += entropyNorm(c);
        f[15] = acc / nom.length;
    }
    return f;
}
function quantile7(s, p) {
    const n = s.length, h = (n - 1) * p, lo = Math.floor(h), hi = Math.min(lo + 1, n - 1);
    return s[lo] + (h - lo) * (s[hi] - s[lo]);
}
const sorted = (a) => Float64Array.from(a).sort();
function groupFlags(toks, cols) {
    const flags = new Array(cols.length).fill(0);
    const s = outerSelect(toks);
    if (s === null)
        return flags;
    const [lo, hi] = outerRange(toks, s), d0 = toks[s].depth;
    const proj = outerProjection(toks, s), aligned = proj.length === cols.length;
    for (let i = lo; i < hi - 1; i++) {
        if (toks[i].depth === d0 && kw(toks[i], "GROUP") && kw(toks[i + 1], "BY")) {
            for (const item of splitCommas(toks, i + 2, clauseEnd(toks, i + 2))) {
                const cand = new Set();
                if (item.length === 1 && item[0].kind === "number" && allDigits(item[0].text)) {
                    const k = Number(item[0].text) - 1;
                    if (k >= 0 && k < cols.length)
                        cand.add(k);
                }
                else {
                    if (item.length === 1)
                        matchName(item[0], cols).forEach((j) => cand.add(j));
                    if (aligned)
                        proj.forEach((p, j) => { if (sameSeq(p, item))
                            cand.add(j); });
                }
                if (cand.size === 1)
                    flags[[...cand][0]] = 1;
            }
        }
    }
    return flags;
}
function aggFlags(toks, cols) {
    const flags = new Array(cols.length).fill(0);
    const s = outerSelect(toks);
    if (s === null)
        return flags;
    const proj = outerProjection(toks, s);
    if (proj.length !== cols.length)
        return flags;
    proj.forEach((p, j) => { if (p.some((t, k) => kw(t, ...AGG) && k + 1 < p.length && p[k + 1].kind === "punct" && p[k + 1].text === "("))
        flags[j] = 1; });
    return flags;
}
function columnFeatures(cols, N, table, toks) {
    const M = cols.length;
    const gflag = groupFlags(toks, cols), aflag = aggFlags(toks, cols);
    return cols.map((c, j) => {
        const f = new Array(28).fill(0);
        f[0] = j / Math.max(M - 1, 1);
        f[1] = c.type === "temporal" ? 1 : 0;
        f[2] = c.type === "quantitative" ? 1 : 0;
        f[3] = c.type === "nominal" ? 1 : 0;
        f[4] = c.type === "identifier" ? 1 : 0;
        f[5] = gflag[j];
        f[6] = aflag[j];
        f[7] = N > 0 ? 1 - c.n / N : 0;
        f[8] = Math.log10(1 + c.K);
        f[9] = c.K / Math.max(c.n, 1);
        f[10] = c.n > 0 && c.K === c.n ? 1 : 0;
        if (c.strs.length) {
            let tot = 0;
            for (const s of c.strs) {
                let k = 0;
                for (const _ of s)
                    k++;
                tot += k;
            }
            f[11] = (tot / c.strs.length) / 50;
        }
        const x = c.num;
        if (c.type === "quantitative" && c.n > 0 && x) {
            const n = c.n;
            let sum = 0;
            for (const v of x)
                sum += v;
            const mu = sum / n;
            let v2 = 0;
            for (const v of x)
                v2 += (v - mu) * (v - mu);
            const variance = v2 / n, sigma = Math.sqrt(variance);
            f[12] = sigma / (Math.abs(mu) + 1e-8);
            let mx = -Infinity, mn = Infinity;
            for (const v of x) {
                if (v > mx)
                    mx = v;
                if (v < mn)
                    mn = v;
            }
            if (n >= 2 && mx !== mn) {
                let a3 = 0, a4 = 0;
                for (const v of x) {
                    const d = v - mu;
                    a3 += d * d * d;
                    a4 += (d * d) * (d * d);
                }
                f[13] = (a3 / n) / (sigma * sigma * sigma + 1e-8);
                f[14] = (a4 / n) / ((sigma * sigma) * (sigma * sigma) + 1e-8) - 3;
            }
            f[15] = x.filter((v) => v < 0).length / n;
            f[16] = x.filter((v) => v === 0).length / n;
            f[19] = (mx - mn) / (Math.abs(mu) + 1e-8);
            const sx = sorted(x), med = quantile7(sx, 0.5);
            f[20] = (quantile7(sx, 0.75) - quantile7(sx, 0.25)) / (Math.abs(med) + 1e-8);
            f[21] = quantile7(sorted(x.map((v) => Math.abs(v - med))), 0.5) / (Math.abs(med) + 1e-8);
        }
        if ((c.type === "quantitative" || c.type === "temporal") && c.n >= 2 && x) {
            let up = 0;
            for (let i = 0; i + 1 < x.length; i++)
                if (x[i + 1] >= x[i])
                    up++;
            f[17] = up / (c.n - 1);
        }
        if (c.type === "temporal" && c.n >= 3 && x) {
            const d = [];
            for (let i = 0; i + 1 < x.length; i++)
                d.push(x[i + 1] - x[i]);
            let s1 = 0;
            for (const v of d)
                s1 += v;
            const md = s1 / d.length;
            let s2 = 0;
            for (const v of d)
                s2 += (v - md) * (v - md);
            f[18] = (s2 / d.length) / (md * md + 1e-8);
        }
        f[22] = table[3];
        f[23] = table[6];
        f[24] = table[10];
        f[25] = table[16];
        f[26] = table[21];
        f[27] = table[22];
        return f;
    });
}
function finalize(vec, defs) {
    const out = new Float32Array(vec.length);
    vec.forEach((v, i) => {
        const [, lo, hi, dflt] = defs[i];
        if (!Number.isFinite(v))
            v = dflt;
        out[i] = Math.min(Math.max(v, lo), hi); // Float32Array storage rounds to nearest-even binary32
    });
    return out;
}
/** Compute the 32 table features and the M x 28 column features of SqlVizSpec-v1.0.0. SQL is never executed. */
export function extractFeatures(sql, schema, rows) {
    const cols = parseInput(schema, rows);
    const N = rows.length, toks = lex(sql);
    const table = finalize([...sqlFeatures(sql, cols), ...globalFeatures(cols, N)], [...SQL_FEATURES, ...GLOBAL_FEATURES]);
    const colraw = columnFeatures(cols, N, Array.from(table), toks);
    return { table, columns: colraw.map((r) => finalize(r, COLUMN_FEATURES)) };
}
/** Convenience: schema + rows from an array of row objects (keys of the first row, in order). */
export function fromObjects(rows) {
    const keys = rows.length ? Object.keys(rows[0]) : [];
    return { schema: keys.map((name) => ({ name })), rows: rows.map((r) => keys.map((k) => r[k] ?? null)) };
}
