# @sqltoviz/core — alpha

Deterministic preview for Node and browsers. No SQL execution, trained ONNX or full feature parity yet. ESM/CJS and declarations. Supports KPI, bar, horizontal bar, line and table; ECharts/Recharts adapters for the three chart types. Recharts output is configuration data, not a React component.

```ts
import {recommend,toEcharts} from '@sqltoviz/core';
const rows=[{category:'A',sales:10},{category:'B',sales:20}];
console.log(toEcharts(recommend('SELECT category,sales FROM totals',rows),rows));
```

Run npm install && npm test && npm pack. Browser WASM/ONNX, full SQL lexer, statistical feature profiler and cross-runtime parity remain future work.


## Model-backed engine (experimental)

```js
import {loadDefaultEngine} from "@sqltoviz/core/node";      // npm i onnxruntime-node
const engine = await loadDefaultEngine();                    // bundled EXPERIMENTAL candidate models, checksum-verified
const rec = await engine.recommend("SELECT dept, SUM(sal) AS total FROM emp GROUP BY dept",
  [{name: "dept"}, {name: "total"}], [["a", 10], ["b", 20], ["c", 5]]);
rec.final_class; rec.model_status; rec.roles; rec.warnings;
```
Browser (WASM): `import {createWebRunner} from "@sqltoviz/core/web"` (needs `onnxruntime-web`); `createWebRunner(url, sha256, "chart"|"role")` returns a runner you pass to `new Engine({chart, role, chartStatus})`. `extractFeatures(sql, schema, rows)` computes the 32 table and 28 column features of SqlVizSpec-v1.0.0 in plain TypeScript (no dependencies). The bundled models are **candidates** (chart: synthetic labels; role: 322 Vega-Lite columns), never scientifically validated; every result says `model_status: "experimental"`. Final models drop in by replacing the files/manifest (or passing your own paths + checksums) - the API and result shape do not change. SQL is never executed.
