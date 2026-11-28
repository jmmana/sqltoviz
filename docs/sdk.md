# SDK quickstart

Build from a checkout while the alpha packages await registry publication.
These examples use precomputed SQL result rows. Each SDK has a deterministic
preview, and the experimental ONNX paths are documented separately.

| SDK | Runtime | Build from the repository root |
| --- | --- | --- |
| [Python](https://github.com/jmmana/sqltoviz/tree/main/packages/python) | Python 3.10+ | `python -m pip install build && python -m build packages/python` |
| [TypeScript](https://github.com/jmmana/sqltoviz/tree/main/packages/npm) | Node.js 20+ | `cd packages/npm && npm install --ignore-scripts && npm pack` |
| [.NET](https://github.com/jmmana/sqltoviz/tree/main/packages/nuget) | .NET 8 or 10 | `dotnet pack packages/nuget/SqlToViz/SqlToViz.csproj -c Release -o artifacts` |

For Python, install the wheel with pip in a virtual environment. For
TypeScript, install the generated .tgz from the application directory. For
.NET, install `SqlToViz` with `dotnet add package SqlToViz --prerelease --source /absolute/path/to/artifacts`
in the consuming project.

## One result, three SDKs

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

## Research and model status

The [research protocol](https://github.com/jmmana/sqltoviz/blob/main/research/paper/PROTOCOL.md)
describes the held-out evaluation. The [model cards](https://github.com/jmmana/sqltoviz/tree/main/model/candidate)
document the training sources, feature contract and limitations. The bundled
ONNX models remain experimental. See the [roadmap](./roadmap.md) for release
and research acceptance criteria.
