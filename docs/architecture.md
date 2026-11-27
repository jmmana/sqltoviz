# Architecture decisions / Decisiones de arquitectura

## Data boundary / Límite de datos

Applications run queries in their own database layer and pass the SQL text and
result rows to SqlToViz. The SDKs and browser preview analyze those inputs
locally. Database connectivity, SQL execution and database-grade dialect
validation are outside the product scope.

Las aplicaciones ejecutan sus consultas en su propia capa de datos y entregan
el SQL y las filas a SqlToViz. La ejecución, la conexión a bases de datos y la
validación completa de dialectos quedan fuera del alcance del producto.

## Contracts / Contratos

The deterministic preview is a small rules-based recommendation that remains
available without an ONNX runtime. Experimental engines use the ordered
[SqlVizSpec feature contract](../spec/sqlvizspec-v1-features.md) and its verified
model manifests. Keep package versions, preview result versions and mathematical
contract versions independent. A model candidate is experimental until its
evaluation establishes a stronger claim.

La vista previa determinista funciona sin ONNX. Los motores experimentales
usan el contrato ordenado SqlVizSpec y manifiestos de modelos verificados.
Las versiones de paquetes, resultados de vista previa y contrato matemático
evolucionan por separado. La evaluación determina qué afirmaciones pueden
hacerse sobre cada modelo.

## Distribution / Distribución

Python, TypeScript and .NET ship as installable libraries. The
[Pages preview](https://jmmana.github.io/sqltoviz/) serves a local playground
and an illustrated chart gallery. Visual adapters map supported outputs to
rendering libraries. Gallery illustrations and documented fixture outputs
have distinct roles.

Python, TypeScript y .NET se distribuyen como bibliotecas instalables. Pages
ofrece un playground local y una galería ilustrada. Los adaptadores convierten
las recomendaciones compatibles en configuraciones para las bibliotecas de
gráficas. La galería ilustra la taxonomía y los casos de prueba verifican el motor.
