"""Render-neutral adapters for the conservative preview subset."""
def _parts(plan,rows):
    kind=plan["chartType"]; enc=plan["encodings"]
    if kind not in ("bar","horizontal_bar","line"):
        raise ValueError("Adapter supports bar, horizontal_bar and line only; use native table/KPI UI")
    x,y=enc["x"],enc["y"]
    return kind,x,y,[r[x] for r in rows],[r[y] for r in rows]

def to_echarts(plan,rows):
    kind,x,y,a,b=_parts(plan,rows)
    cat={"type":"category","data":a,"name":x}; num={"type":"value","name":y}
    return {"xAxis":num if kind=="horizontal_bar" else cat,"yAxis":cat if kind=="horizontal_bar" else num,"series":[{"type":"line" if kind=="line" else "bar","data":b}]}

def to_vegalite(plan,rows):
    kind,x,y,_,_=_parts(plan,rows)
    cat={"field":x,"type":"temporal" if kind=="line" else "nominal"}; num={"field":y,"type":"quantitative"}
    return {"$schema":"https://vega.github.io/schema/vega-lite/v5.json","data":{"values":rows},"mark":"line" if kind=="line" else "bar","encoding":{"x":num if kind=="horizontal_bar" else cat,"y":cat if kind=="horizontal_bar" else num}}

def to_plotly(plan,rows):
    kind,x,y,a,b=_parts(plan,rows)
    trace={"type":"scatter" if kind=="line" else "bar","x":b if kind=="horizontal_bar" else a,"y":a if kind=="horizontal_bar" else b}
    if kind=="line": trace["mode"]="lines+markers"
    if kind=="horizontal_bar": trace["orientation"]="h"
    return {"data":[trace],"layout":{}}
