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
