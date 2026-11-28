#!/usr/bin/env python3
"""Numerical-faithfulness cases for the statistical detectors with EXACT reference values (rational/decimal arithmetic, stdlib only).
Usage: python parity/tools/gen_faithfulness.py OUT.json [N=1500] [SEED=20261127]
Each runtime (Python, TypeScript, .NET) replays the file when SQLTOVIZ_FAITH is set and reports its maximum error against the exact reference.
Boundary cases (|score - threshold| < 1e-9 relative, coverage ties) are excluded: they are decided by the last bit of the input, not by faithfulness."""
import json, math, random, sys
from decimal import Decimal, getcontext
from fractions import Fraction

getcontext().prec = 120
out, n, seed = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1500, int(sys.argv[3]) if len(sys.argv) > 3 else 20261127
rng = random.Random(seed)
K = Fraction(0.6744897501960817)


def vals(m, scale, off):
    return [rng.choice([round(rng.gauss(off, 1) * scale, rng.choice([0, 3, 9])), rng.randint(-1000, 1000) * scale]) for _ in range(m)]


def med(xs):
    s = sorted(xs); k = len(s)
    return s[k // 2] if k % 2 else (s[k // 2 - 1] + s[k // 2]) / 2


def mad_case():
    m = rng.randint(3, 60); scale = 10.0 ** rng.randint(-8, 8); x = vals(m, scale, rng.choice([0, 5, 1e3]))
    if rng.random() < 0.5: x[rng.randrange(m)] = x[rng.randrange(m)] + rng.choice([-1, 1]) * scale * rng.choice([5, 20, 100])
    inp = [None if rng.random() < 0.05 else v for v in x]
    pairs = [(i, Fraction(v)) for i, v in enumerate(inp) if v is not None and math.isfinite(v)]
    if len(pairs) < 3: return {"kind": "mad", "values": inp, "expected": {"status": "insufficient_samples", "outliers": []}}
    c = med([v for _, v in pairs]); mad = med([abs(v - c) for _, v in pairs])
    if mad == 0: return {"kind": "mad", "values": inp, "expected": {"status": "zero_mad", "median": float(c), "mad": 0.0, "outliers": []}}
    sc = [(i, K * (v - c) / mad) for i, v in pairs]
    if any(abs(abs(float(s)) - 3.5) < 3.5e-9 for _, s in sc): return None
    return {"kind": "mad", "values": inp, "expected": {"status": "ok", "median": float(c), "mad": float(mad), "outliers": [{"index": i, "score": float(s)} for i, s in sc if abs(s) > Fraction(7, 2)]}}


def pearson_case():
    m = rng.randint(3, 50); scale = 10.0 ** rng.randint(-8, 8); off = rng.choice([0, 1, 1e3, 1e6])
    a = vals(m, scale, off); b = [0.7 * v + rng.gauss(0, 1) * scale for v in a]
    xs = [None if rng.random() < 0.04 else v for v in a]; ys = [None if rng.random() < 0.04 else v for v in b]
    p = [(Decimal(x), Decimal(y)) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(p) < 3: return {"kind": "pearson", "xs": xs, "ys": ys, "expected": {"status": "insufficient_samples", "r": None}}
    k = len(p); ma = sum(x for x, _ in p) / k; mb = sum(y for _, y in p) / k
    sxx = sum((x - ma) ** 2 for x, _ in p); syy = sum((y - mb) ** 2 for _, y in p); sxy = sum((x - ma) * (y - mb) for x, y in p)
    if sxx == 0 or syy == 0: return {"kind": "pearson", "xs": xs, "ys": ys, "expected": {"status": "constant_column", "r": None}}
    return {"kind": "pearson", "xs": xs, "ys": ys, "expected": {"status": "ok", "r": float(sxy / (sxx * syy).sqrt())}}


def temporal_case():
    m = rng.randint(2, 30); scale = 10.0 ** rng.randint(-6, 6); x = [rng.choice([0, round(rng.gauss(5, 3) * scale, 6), -round(rng.random() * scale, 6)]) for _ in range(m)]
    inp = [None if rng.random() < 0.1 else v for v in x]; exp = []
    for i in range(1, m):
        a, b = inp[i - 1], inp[i]
        if a is None or b is None: exp.append({"status": "missing", "delta": None, "relative_change": None}); continue
        d = Fraction(b) - Fraction(a)
        if a == 0: exp.append({"status": "zero_baseline", "delta": float(d), "relative_change": None}); continue
        exp.append({"status": "ok", "delta": float(d), "relative_change": float(d / abs(Fraction(a)))})
    return {"kind": "temporal", "values": inp, "expected": exp}


def pareto_case():
    m = rng.randint(2, 30); scale = 10.0 ** rng.randint(-6, 6); w = [round(abs(rng.gauss(10, 8)) * scale, 6) for _ in range(m)]
    if rng.random() < 0.3: w[rng.randrange(m)] = 0.0
    if max(w) == 0: return None
    F = [Fraction(v) for v in w]; tot = sum(F); order = sorted(range(m), key=lambda i: (-F[i], i)); run = Fraction(0); reached = False; items = []
    for i in order:
        share = F[i] / tot; run = min(Fraction(1), run + share)
        if abs(float(run) - 0.8) < 1e-9: return None
        items.append({"index": i, "share": float(share), "cumulative": float(run), "included": (not reached) and F[i] > 0}); reached = reached or run >= Fraction(8, 10) - Fraction(1, 10 ** 15)
    return {"kind": "pareto", "values": w, "coverage": 0.8, "expected": {"status": "ok", "items": items}}


cases = []
gens = [mad_case, pearson_case, temporal_case, pareto_case]
while len(cases) < n:
    c = gens[len(cases) % 4]()
    if c: cases.append(c)
json.dump({"seed": seed, "n": len(cases), "tolerance": {"relative": 1e-12, "pearson_abs": 1e-10}, "cases": cases}, open(out, "w"))
print(len(cases), "cases ->", out)
