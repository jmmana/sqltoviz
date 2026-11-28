# sqltoviz — alpha

Deterministic preview for Node and browsers, with ESM/CJS and declarations. Supports KPI, bar, horizontal bar, line and table. The model-backed Node and browser entry points use experimental ONNX models, documented below.

```ts
import {recommend,toEcharts} from 'sqltoviz';
const rows=[{category:'A',sales:10},{category:'B',sales:20}];
console.log(toEcharts(recommend('SELECT category,sales FROM totals',rows),rows));
```

Run `npm install --ignore-scripts && npm test && npm pack` from this package directory.


## Model-backed engine (experimental)

```js
import {loadDefaultEngine} from "sqltoviz/node";      // npm i onnxruntime-node
const engine = await loadDefaultEngine();                    // bundled EXPERIMENTAL candidate models, checksum-verified
const rec = await engine.recommend("SELECT dept, SUM(sal) AS total FROM emp GROUP BY dept",
  [{name: "dept"}, {name: "total"}], [["a", 10], ["b", 20], ["c", 5]]);
rec.final_class; rec.model_status; rec.roles; rec.warnings;
```
Browser (WASM): `import {createWebRunner} from "sqltoviz/web"` (needs `onnxruntime-web`); `createWebRunner(url, sha256, "chart"|"role")` returns a runner you pass to `new Engine({chart, role, chartStatus})`. `extractFeatures(sql, schema, rows)` computes the 32 table and 28 column features of SqlVizSpec-v1.0.0 in plain TypeScript (no dependencies). The bundled models are **candidates** (chart: synthetic labels; role: 322 Vega-Lite columns), never scientifically validated; every result says `model_status: "experimental"`. Final models drop in by replacing the files/manifest (or passing your own paths + checksums) - the API and result shape do not change. SQL is never executed.

## Renderer adapters / Adaptadores de gráficos

For a deterministic preview plan and its original rows, `toEcharts(plan, rows)`
returns options for ECharts and `toRecharts(plan, rows)` returns the chart name,
layout, category/value keys and data. Use the category key on the category axis
and the value key on the numeric axis. For a Recharts vertical layout, the
numeric axis is X and the category axis is Y. Supported charts are bar,
horizontal bar and line. Render KPI and table plans directly in the application.

Usa el plan y sus filas originales. `toEcharts` devuelve opciones de ECharts y
`toRecharts` devuelve el tipo, la orientación, las claves y los datos. En barras
horizontales de Recharts, X es numérico e Y es categórico. Los adaptadores
admiten barras y líneas. Para KPI y tabla, renderiza el plan en la aplicación.
