# Deterministic preview response / Respuesta de vista previa determinista

The [JSON Schema](preview-response-v0.1.schema.json) defines the portable
preview response. Python and TypeScript preview plans already use this shape.
For .NET, map the native Plan's ChartType, Reason and Mode to chartType,
reason and mode. Create encodings from its non-null X and Y as x and y, and
set contract_version to preview-v0.1. The optional warnings and insights
may be omitted. Insights payloads are SDK-specific.

El esquema define la respuesta portable de vista previa. Los planes de
Python y TypeScript ya usan esta forma. Para .NET, mapea ChartType, Reason y
Mode a chartType, reason y mode. Usa X e Y cuando tengan valor para formar
encodings.x y encodings.y. Establece contract_version en preview-v0.1.
Warnings e insights son opcionales y el contenido de insights depende del SDK.

Use contract_version to select the schema. Adding an optional top-level field
is compatible with v0.1. Changes to required fields, chart values, or encoding
semantics require a new contract version. Package release versions are independent.
The experimental engine uses the separate [SqlVizSpec feature contract](sqlvizspec-v1-features.md).

Usa contract_version para seleccionar el esquema. Agregar un campo opcional
de primer nivel es compatible con v0.1. Cambiar campos requeridos, valores
de gráfico o el significado de los ejes requiere otra versión del contrato.
Las versiones de paquetes son independientes. El motor experimental usa
el contrato de características SqlVizSpec.

## Verification / Verificación

Run from the repository root / Ejecuta desde la raíz del repositorio:

```sh
python -m pip install jsonschema
python spec/verify_preview_response.py
```
