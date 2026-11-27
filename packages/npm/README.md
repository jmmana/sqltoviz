# @sqltoviz/core — alpha

Deterministic preview for Node and browsers. No SQL execution, trained ONNX or full feature parity yet. ESM/CJS and declarations. Supports KPI, bar, horizontal bar, line and table; ECharts/Recharts adapters for the three chart types. Recharts output is configuration data, not a React component.

```ts
import {recommend,toEcharts} from '@sqltoviz/core';
const rows=[{category:'A',sales:10},{category:'B',sales:20}];
console.log(toEcharts(recommend('SELECT category,sales FROM totals',rows),rows));
```

Run npm install && npm test && npm pack. Browser WASM/ONNX, full SQL lexer, statistical feature profiler and cross-runtime parity remain future work.
