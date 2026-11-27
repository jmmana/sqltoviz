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
To try it locally: `cd packages/npm && npm install --ignore-scripts && npm run build`, then `node site/build-engine.mjs` (generates `site/sdk`, `site/models`, `site/vendor`; not committed) and serve `site/`. Tests: `node --test site/*.test.mjs`; real-browser test: `node site/e2e/playground.e2e.mjs` (needs `npm i --no-save playwright` and `npx playwright install chromium`).

El botón **Run experimental model** ejecuta en el navegador los dos modelos ONNX candidatos (gráfico y roles) con `onnxruntime-web` (WebAssembly de un hilo). No se sube nada: el runtime, los modelos y el SDK se sirven desde este sitio (la primera vez descarga unos 14 MB). Los modelos son **candidatos**, sin validación científica; el panel y el resultado lo indican.
