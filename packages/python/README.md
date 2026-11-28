# SqlToViz Python alpha

The package exposes two recommendation APIs. Both take SQL text and existing result rows, and run locally.

| API | Input | Result |
| --- | --- | --- |
| `recommend(sql, rows)` | SQL text and a list of row dictionaries | `preview-v0.1` plan with chart type, encodings, warnings and numeric insights |
| `Engine.recommend(sql, schema, rows)` | SQL text, column schema and positional rows | Versioned feature-contract result with class, roles and model status |

The deterministic preview supports KPI, bar, horizontal bar, line and table.
It accepts 1–5,000 rows with identical sets of 1–50 named scalar columns.
Invalid rows or empty SQL raise `ValueError`. The experimental engine and its
optional ONNX dependency are described below.

```python
from sqltoviz import recommend, to_echarts
rows = [{"category":"A","sales":10},{"category":"B","sales":20}]
plan = recommend("SELECT category, SUM(sales) FROM sales GROUP BY category", rows)
print(plan)
print(to_echarts(plan, rows))
```

Run `python -m unittest discover -s tests` from this directory. Build with `python -m build`. Install the generated wheel in a clean environment before release. Adapters support bar, horizontal bar and line only; native KPI/table rendering is the caller's responsibility.


## Model-backed engine (experimental)

```python
from sqltoviz import Engine           # pip install "sqltoviz[onnx]"
engine = Engine.default()             # bundled EXPERIMENTAL candidate models (checksum-verified)
rec = engine.recommend("SELECT dept, SUM(sal) AS total FROM emp GROUP BY dept",
                       [{"name": "dept"}, {"name": "total"}], [["a", 10.0], ["b", 20.0], ["c", 5.0]])
rec["final_class"], rec["model_status"], rec["roles"], rec["warnings"]
```
`Engine` computes the 32 table and 28 column features of SqlVizSpec-v1.0.0 (pure Python; the contract hash is pinned and checked by CI), scores the 10 base classes with the chart ONNX model, applies hard semantic constraints (fail-closed to `table`) and infers column roles with the role model. **The bundled models are candidates**: the chart model is trained on synthetic labels and the role model on 322 Vega-Lite columns; neither has human validation, and every result says `model_status: "experimental"`. To use final models without changing any code, pass them in: `Engine(chart_model=path, role_model=path, manifest={"chart": {"sha256": ..., "status": "validated"}, "role": {...}})` or replace `sqltoviz/models/manifest.json`; the API and result shape are unchanged. `Engine()` without models is rules-only. SQL is never executed.


## Resumen en español

`recommend(sql, rows)` recibe el SQL y una lista de diccionarios con las filas.
Devuelve un plan determinista `preview-v0.1` con el gráfico, sus campos, avisos e
insights numéricos. `Engine.recommend(sql, schema, rows)` recibe por separado el
esquema y las filas posicionales. Devuelve la clase del gráfico, los roles de
columna y el estado del modelo. Los modelos incluidos son experimentales. Ambas
interfaces procesan las filas localmente y no ejecutan el SQL.

## Chart adapters / Adaptadores de gráficos

`to_echarts(plan, rows)` returns ECharts options, `to_vegalite(plan, rows)`
returns a Vega-Lite specification, and `to_plotly(plan, rows)` returns a
Plotly figure dictionary. Pass the same rows used for the deterministic
`recommend` call. The three adapters support bar, horizontal bar and line.
KPI and table plans raise `ValueError` so callers can render those directly.

Los tres adaptadores generan configuraciones para sus bibliotecas de gráficos.
Usa las mismas filas que entregaste a `recommend`. Admiten barras verticales,
barras horizontales y líneas. Para KPI y tabla, renderiza el plan directamente.
