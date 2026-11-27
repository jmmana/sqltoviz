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
