# Guía rápida de los SDK

Compila desde un clon del repositorio mientras los paquetes alfa esperan su
publicación. Los ejemplos usan resultados SQL ya calculados. Cada SDK ofrece
una vista previa determinista y documenta por separado cómo usar ONNX experimental.

| SDK | Entorno | Compilación desde la raíz del repositorio |
| --- | --- | --- |
| [Python](https://github.com/jmmana/sqltoviz/tree/main/packages/python) | Python 3.10+ | `python -m pip install build && python -m build packages/python` |
| [TypeScript](https://github.com/jmmana/sqltoviz/tree/main/packages/npm) | Node.js 20+ | `cd packages/npm && npm install --ignore-scripts && npm pack` |
| [.NET](https://github.com/jmmana/sqltoviz/tree/main/packages/nuget) | .NET 8 o 10 | `dotnet pack packages/nuget/SqlToViz/SqlToViz.csproj -c Release -o artifacts` |

En Python, instala la rueda con pip en un entorno virtual. En TypeScript,
instala el archivo .tgz generado desde el proyecto consumidor. En .NET,
instala `SqlToViz` con `dotnet add package SqlToViz --prerelease --source /ruta/absoluta/a/artifacts`
desde el proyecto consumidor.

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
[hoja de ruta](../roadmap.md) recoge los criterios de lanzamiento e investigación.
