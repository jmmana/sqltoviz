# Guía rápida de los SDK

Instala los paquetes alfa desde los registros públicos (son versiones
preliminares, por eso se necesitan las opciones indicadas). Los ejemplos usan
resultados SQL ya calculados. Cada SDK ofrece una vista previa determinista y
documenta por separado cómo usar ONNX experimental.

| SDK | Entorno | Instalación |
| --- | --- | --- |
| [Python](https://pypi.org/project/sqltoviz/) | Python 3.10+ | `pip install --pre sqltoviz` (agrega `"sqltoviz[onnx]"` para los modelos experimentales) |
| [TypeScript](https://www.npmjs.com/package/sqltoviz) | Node.js 20+ | `npm install sqltoviz@alpha` |
| [.NET](https://www.nuget.org/packages/SqlToViz) | .NET 8 o 10 | `dotnet add package SqlToViz --prerelease` (y `SqlToViz.Onnx` para los modelos experimentales) |

Para compilar desde un clon, usa `python -m build packages/python`,
`cd packages/npm && npm install --ignore-scripts && npm pack` o
`dotnet pack packages/nuget/SqlToViz/SqlToViz.csproj -c Release -o artifacts`.

## Un resultado, tres SDK

```python
from sqltoviz import recommend

plan = recommend("SELECT 42 AS total", [{"total": 42}])
assert plan["chartType"] == "kpi"
```

```js
import { recommend } from 'sqltoviz';

const plan = recommend('SELECT 42 AS total', [{ total: 42 }]);
console.assert(plan.chartType === 'kpi');
```

```csharp
var plan = SqlToViz.Preview.Recommend(
    "SELECT 42 AS total",
    new[] { new Dictionary<string, object?> { ["total"] = 42 } });
Console.WriteLine(plan.ChartType); // kpi
```

## Investigación y estado de los modelos

El [protocolo de investigación](https://github.com/jmmana/sqltoviz/blob/main/research/paper/PROTOCOL.md)
describe la evaluación con datos reservados. Las [fichas de los modelos](https://github.com/jmmana/sqltoviz/tree/main/model/candidate)
indican las fuentes de entrenamiento, el contrato de características y las
limitaciones. Los modelos ONNX incluidos siguen en fase experimental. La
[hoja de ruta](/roadmap) recoge los criterios de lanzamiento e investigación.
