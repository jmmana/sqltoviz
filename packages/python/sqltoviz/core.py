import math
from datetime import date
from .statistics import mad_outliers, pareto, pearson, temporal_shifts

def _numeric(v):
    return type(v) in (int,float) and abs(v)<=1.7976931348623157e308 and math.isfinite(v)

def _date(v):
    if not isinstance(v,str): return False
    try: return date.fromisoformat(v).isoformat()==v
    except ValueError: return False

def recommend(
    sql, rows, *, temporal_column=None, pareto_column=None,
    pareto_additive=False, correlation_columns=None,
):
    """Return a conservative, rules-only plan. Never execute SQL."""
    if not isinstance(sql,str) or not sql.strip() or len(sql)>20000:
        raise ValueError("SQL must contain 1–20000 characters")
    if not isinstance(rows,list) or not 1<=len(rows)<=5000 or not all(isinstance(r,dict) for r in rows):
        raise ValueError("Expected 1–5000 row dictionaries")
    keys=list(rows[0])
    if not 1<=len(keys)<=50 or not all(isinstance(k,str) and k for k in keys):
        raise ValueError("Expected 1–50 named columns")
    for r in rows:
        if set(r)!=set(keys) or any(v is not None and not (isinstance(v,(str,bool)) or _numeric(v)) for v in r.values()):
            raise ValueError("Rows must have identical scalar columns")
    nums=[k for k in keys if all(_numeric(r[k]) for r in rows)]
    cats=[k for k in keys if all(isinstance(r[k],str) and r[k] for r in rows)]
    chart="table"; enc={}; reason="No supported safe chart for shape"
    if len(rows)==len(keys)==len(nums)==1:
        chart="kpi"; enc={"y":nums[0]}; reason="One numeric scalar"
    elif len(keys)==2 and len(nums)==len(cats)==1 and len(rows)<=100:
        x,y=cats[0],nums[0]; labels=[r[x] for r in rows]
        if len(set(labels))==len(labels):
            temporal= len(labels)>=4 and all(_date(v) for v in labels) and labels==sorted(labels)
            chart="line" if temporal else "horizontal_bar" if len(rows)>12 else "bar"
            enc={"x":x,"y":y}; reason="Ordered ISO dates" if temporal else "Unique categories"
    insights={k:mad_outliers([r[k] for r in rows]) for k in nums}
    plan = {"contract_version":"preview-v0.1","mode":"deterministic-preview","chartType":chart,"encodings":enc,"reason":reason,"insights":insights,"warnings":["No ONNX model; stacking and other metadata-dependent charts are not supported by this preview."]}

    def numeric_values(column):
        if not isinstance(column, str) or column not in keys:
            raise ValueError("Detector column must name an existing result column")
        values = [row[column] for row in rows]
        if any(value is not None and not _numeric(value) for value in values):
            raise ValueError("Detector columns must contain only numbers or null")
        return values

    diagnostics = {}
    if temporal_column is not None:
        diagnostics["temporal"] = temporal_shifts(numeric_values(temporal_column))
    if pareto_column is not None:
        if not isinstance(pareto_additive, bool):
            raise ValueError("Pareto additivity must be an explicit boolean")
        diagnostics["pareto"] = pareto(numeric_values(pareto_column), additive=pareto_additive)
    if correlation_columns is not None:
        if not isinstance(correlation_columns, (tuple, list)) or len(correlation_columns) != 2:
            raise ValueError("Correlation requires two result column names")
        left, right = correlation_columns
        if left == right:
            raise ValueError("Correlation requires distinct result columns")
        diagnostics["correlation"] = pearson(numeric_values(left), numeric_values(right))
    if diagnostics:
        plan["diagnostics"] = diagnostics
    return plan
