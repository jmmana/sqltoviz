"""Deterministic statistical detectors; independent of ONNX."""
import math
import statistics as st

def _number(x):
    return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)

def _values(values):
    return [(i,float(x)) for i,x in enumerate(values) if _number(x)]

def mad_outliers(values, threshold=3.5):
    """Modified Z-score; zero MAD is explicitly indeterminate, not a fabricated score."""
    if not _number(threshold) or threshold<=0:
        raise ValueError("threshold must be finite and positive")
    pairs=_values(values)
    if len(pairs)<3:
        return {"status":"insufficient_samples","outliers":[]}
    center=st.median(x for _,x in pairs)
    mad=st.median(abs(x-center) for _,x in pairs)
    if mad==0:
        return {"status":"zero_mad","median":center,"mad":0,"outliers":[]}
    scores=[(i,0.6744897501960817*((x-center)/mad)) for i,x in pairs]
    if not all(math.isfinite(z) for _,z in scores):
        return {"status":"numeric_overflow","outliers":[]}
    return {"status":"ok","median":center,"mad":mad,"outliers":[{"index":i,"score":z} for i,z in scores if abs(z)>threshold]}

def temporal_shifts(values):
    """Adjacent already-ordered observations; missing cells break adjacency."""
    result=[]
    for i,(a,b) in enumerate(zip(values,values[1:]),1):
        if not (_number(a) and _number(b)):
            result.append({"index":i,"status":"missing","delta":None,"relative_change":None})
            continue
        a,b=float(a),float(b)
        delta=b-a
        if not math.isfinite(delta):
            result.append({"index":i,"status":"numeric_overflow","delta":None,"relative_change":None})
            continue
        change=delta/abs(a) if a else None
        if change is not None and not math.isfinite(change):
            result.append({"index":i,"status":"numeric_overflow","delta":delta,"relative_change":None})
            continue
        result.append({"index":i,"status":"ok" if a else "zero_baseline","delta":delta,"relative_change":change})
    return result

def pareto(values, coverage=0.8, *, additive=False):
    """Require explicit additivity evidence; input categories must be disjoint."""
    if not _number(coverage) or not 0<coverage<=1:
        raise ValueError("coverage must be in (0,1]")
    if not additive:
        return {"status":"unknown_additivity","items":[]}
    pairs=_values(values)
    if len(pairs)!=len(values) or any(x<0 for _,x in pairs):
        return {"status":"invalid_weights","items":[]}
    scale=max((x for _,x in pairs),default=0)
    if scale==0:
        return {"status":"zero_total","items":[]}
    ordered=sorted(pairs,key=lambda p:(-p[1],p[0]))
    total=math.fsum(x/scale for _,x in ordered)
    running=0.0
    items=[]
    reached=False
    for i,x in ordered:
        share=(x/scale)/total
        running=min(1.0,running+share)
        included=not reached and x>0
        items.append({"index":i,"share":share,"cumulative":running,"included":included})
        reached=reached or running>=coverage-1e-15
    return {"status":"ok","items":items}

def pearson(xs,ys):
    """Pairwise complete Pearson correlation; no p-value or causal claim."""
    if len(xs)!=len(ys):
        raise ValueError("paired arrays must have equal length")
    pairs=[(float(x),float(y)) for x,y in zip(xs,ys) if _number(x) and _number(y)]
    n=len(pairs)
    if n<3:
        return {"status":"insufficient_samples","n":n,"r":None}
    a,b=zip(*pairs)
    sa,sb=max(map(abs,a)),max(map(abs,b))
    if not sa or not sb:
        return {"status":"constant_column","n":n,"r":None}
    a=[x/sa for x in a]; b=[y/sb for y in b]
    ma,mb=st.mean(a),st.mean(b)
    da=[x-ma for x in a]; db=[y-mb for y in b]
    na,nb=math.hypot(*da),math.hypot(*db)
    if not na or not nb:
        return {"status":"constant_column","n":n,"r":None}
    r=math.fsum((x/na)*(y/nb) for x,y in zip(da,db))
    return {"status":"ok","n":n,"r":max(-1.0,min(1.0,r))}
