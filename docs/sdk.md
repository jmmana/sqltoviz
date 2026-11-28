# SDK quickstart

The alpha packages are published on PyPI, npm and NuGet. These examples use precomputed SQL result rows. Each SDK has a deterministic
preview, and the experimental ONNX paths are documented separately.

| SDK | Runtime | Install (0.1.0 alpha 2) |
| --- | --- | --- |
| [Python](https://pypi.org/project/sqltoviz/) | Python 3.10+ | `python -m pip install --pre sqltoviz` |
| [TypeScript](https://www.npmjs.com/package/sqltoviz) | Node.js 20+ | `npm install sqltoviz@0.1.0-alpha.2` |
| [.NET](https://www.nuget.org/packages/SqlToViz) | .NET 8 or 10 | `dotnet add package SqlToViz --prerelease` |

Install in a virtual environment (Python) or a fresh project. `SqlToViz.Onnx`
is a separate NuGet package carrying the experimental ONNX models (candidates
without human validation). To build from source, see the
[README](https://github.com/jmmana/sqltoviz#readme).

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
ONNX models remain experimental. See the [roadmap](/roadmap) for release
and research acceptance criteria.
