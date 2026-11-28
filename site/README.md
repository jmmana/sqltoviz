# Browser preview / Vista previa en el navegador

Serve this directory with a static HTTP server. Copy `docs/assets` into
`site/assets` to see the gallery. The playground analyzes SQL text and supplied
rows locally. It uses deterministic rules and supports KPI, bar, horizontal bar,
line and table previews. The gallery contains 21 illustrations.

Sirve este directorio con un servidor HTTP estático. Copia `docs/assets` en
`site/assets` para ver la galería. El playground analiza localmente el texto SQL
y las filas proporcionadas. Usa reglas deterministas y muestra KPI, barras
verticales y horizontales, líneas y tablas. La galería contiene 21 ilustraciones.

## Reproduce the demos / Reproduce los ejemplos

Choose a scenario and click **Load example**. The playground fills both editors
and analyzes the result. You can also load `scenarios.sql` into a fresh SQLite
database and run the SQL shown in the editor. The tests run each query against the
fixture and verify its rows, recommended chart, and warning count.

Elige un escenario y pulsa **Load example**. El playground llena ambos editores
y analiza el resultado. También puedes cargar `scenarios.sql` en una base SQLite
nueva y ejecutar la consulta del editor. Las pruebas verifican las filas, el
gráfico recomendado y el número de avisos para cada consulta.

| Scenario / Escenario | Expected result / Resultado esperado |
| --- | --- |
| Category comparison / Comparación por categoría | Bar chart / Barras |
| Monthly trend / Tendencia mensual | Line chart / Líneas |
| Non-additive averages / Promedios no aditivos | Bar chart with stacking warning / Barras con aviso sobre apilamiento |
| Scalar KPI / KPI de valor único | KPI |

Run the tests from the repository root with Node.js 22.13 or later.
Ejecuta las pruebas desde la raíz del repositorio con Node.js 22.13 o posterior.

```sh
node --test site/*.test.mjs
```

## Appearance / Apariencia

The preview follows the system color scheme until you select a theme. The
toggle keeps your choice on this browser when local storage is available.

La vista previa sigue el esquema de color del sistema hasta que elijas un tema.
El selector conserva la elección en este navegador cuando el almacenamiento
local está disponible.

## Experimental ONNX model / Modelo ONNX experimental

The **Run experimental model** button runs the two candidate ONNX models (chart + role) in the browser with `onnxruntime-web` (single-thread WebAssembly). Nothing is uploaded; the runtime, models and SDK are served from this site (first run downloads about 14 MB of WebAssembly). The models are **candidates**: trained on synthetic labels (chart) and 322 Vega-Lite columns (role), never scientifically validated; the panel and the result say so.
To try it locally: `cd packages/npm && npm install --ignore-scripts && npm run build`, then `node site/build-engine.mjs` (generates `site/sdk`, `site/models`, `site/vendor`; not committed) and serve `site/`. Tests: `node --test site/*.test.mjs`; real-browser test on Chromium/Firefox/WebKit: `BROWSERS=all node site/e2e/playground.e2e.mjs` (default chromium only; needs `npm i --no-save playwright@1.65.1` and `npx playwright install chromium firefox webkit`); bundle size and cold start: `BROWSERS=all node site/e2e/measure.mjs` (results in docs/PERFORMANCE.md).

El botón **Run experimental model** ejecuta en el navegador los dos modelos ONNX candidatos (gráfico y roles) con `onnxruntime-web` (WebAssembly de un hilo). No se sube nada: el runtime, los modelos y el SDK se sirven desde este sitio (la primera vez descarga unos 14 MB). Los modelos son **candidatos**, sin validación científica; el panel y el resultado lo indican.

## Editors / Editores

Use **Format JSON** to indent the result rows. Invalid JSON stays in the
editor, with a message explaining the formatting failure. Press Ctrl+Enter
or Cmd+Enter in either editor to run the deterministic analysis.

Usa **Formatear JSON** para indentar las filas. Si la sintaxis es inválida,
el texto permanece en el editor y aparece un aviso. Pulsa Ctrl+Enter o
Cmd+Enter en cualquiera de los editores para ejecutar el análisis determinista.

## ECharts renderer and statistical insights / Renderizador ECharts e hallazgos estadísticos

The **Chart renderer** selector switches the recommendation between the built-in SVG and Apache ECharts 5.6.0, driven by the SDK adapter `toEcharts()` (bar, horizontal bar and line; other chart types keep the built-in renderer and say so). ECharts is copied from `packages/npm` devDependencies by `node site/build-engine.mjs` into `site/vendor/echarts` (git-ignored) and loaded lazily from the same origin: no CDN, no external request, SQL and rows stay in the page. Points flagged by the MAD detector are highlighted.

The **Statistical insights** panel comes only from the SDK detectors (`madOutliers`, `temporalShifts`, `pareto`, `pearson`) and prints their explicit statuses (`zero_mad`, `insufficient_samples`, `unknown_additivity`, `zero_baseline`, `constant_column`...) instead of inventing numbers. Pareto shares are computed only after you tick "Values are additive", because additivity cannot be inferred from the SQL. Both are bilingual (EN/ES) and covered by `site/insights.test.mjs` and the real-browser e2e on Chromium, Firefox and WebKit.

El selector **Renderizador de gráficos** alterna entre el SVG integrado y Apache ECharts 5.6.0 mediante el adaptador `toEcharts()` del SDK, cargado localmente (sin CDN). El panel de **Hallazgos estadísticos** usa solo los detectores del SDK y muestra sus estados explícitos; Pareto requiere confirmar la aditividad.
