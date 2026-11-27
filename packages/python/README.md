# SqlToViz Python alpha

Development preview. No trained ONNX model, no SQL execution and no claim of full SqlVizSpec parity. Supports KPI, bar, horizontal bar, line and table fallback. Other chart types require future semantic constraints. Optional ONNX loader validates checksum and tensor schema; real-model tests remain pending.

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
