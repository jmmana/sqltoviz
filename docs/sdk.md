# SDK quickstart

Install the alpha packages from the public registries (versions are
pre-releases, so the flags below are required). These examples use precomputed
SQL result rows. Each SDK has a deterministic preview, and the experimental
ONNX paths are documented separately.

| SDK | Runtime | Install |
| --- | --- | --- |
| [Python](https://pypi.org/project/sqltoviz/) | Python 3.10+ | `pip install --pre sqltoviz` (add `"sqltoviz[onnx]"` for the experimental models) |
| [TypeScript](https://www.npmjs.com/package/sqltoviz) | Node.js 20+ | `npm install sqltoviz@alpha` |
| [.NET](https://www.nuget.org/packages/SqlToViz) | .NET 8 or 10 | `dotnet add package SqlToViz --prerelease` (and `SqlToViz.Onnx` for the experimental models) |

To build from a checkout instead, use `python -m build packages/python`,
`cd packages/npm && npm install --ignore-scripts && npm pack`, or
`dotnet pack packages/nuget/SqlToViz/SqlToViz.csproj -c Release -o artifacts`.

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

## Concrete outputs (additive, TypeScript so far)

`specializeOutputs(columns, rows, metadata, baseScores, roles, baseEligibility)` (`sqltoviz`, `sqltoviz/web`, `sqltoviz/node`) refines a base class into one of the 21 outputs of `SqlVizSpec-Outputs-v1.0.0` (`spec/OUTPUTS_V1.md`) using deterministic preconditions, and returns `{output, encodings, params, rejected, fallback_chain}`. It mirrors the Python `specialize_outputs`; the .NET port is pending. The thresholds (category caps, minimum sample sizes, bin rule, whisker factor) are design choices, not validated values. The 120 fixtures in `parity/outputs_v1.json` prove that the runtimes agree with each other, not that the rules pick the right chart.

## Research and model status

The [research protocol](https://github.com/jmmana/sqltoviz/blob/main/research/paper/PROTOCOL.md)
describes the held-out evaluation. The [model cards](https://github.com/jmmana/sqltoviz/tree/main/model/candidate)
document the training sources, feature contract and limitations. The bundled
ONNX models remain experimental. See the [roadmap](/roadmap) for release
and research acceptance criteria.
