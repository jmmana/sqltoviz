<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/logo-dark.svg"><img src="docs/assets/logo-light.svg" width="280" alt="SqlToViz"></picture></p>
<p align="center"><img src="docs/assets/hero-en.svg" width="100%" alt="SqlToViz — 21 visualizations"></p>

<p align="center"><a href="README.md">English</a> · <a href="README.es.md">Español</a> · <a href="docs/roadmap.md">Roadmap</a> · <a href="spec/chart-taxonomy-v1.md">SqlVizSpec</a></p>

![Pre-alpha](https://img.shields.io/badge/status-pre--alpha-818cf8) ![Python](https://img.shields.io/badge/Python-planned-3776AB) ![TypeScript](https://img.shields.io/badge/TypeScript-planned-3178C6) ![.NET](https://img.shields.io/badge/.NET-8%20%7C%2010-512BD4)

> **Pre-alpha: illustrative images, not SDK executions. Model, packages and playground pending.**

## What is SqlToViz?

Query-aware visualization recommendation from SQL and result rows, with planned local ONNX inference and deterministic semantic validation.

## 21 visualization gallery

Each image links to a fixture with SQL, synthetic rows, metadata, expected output and explanation.

| **kpi** | **gauge** | **bar** |
| :---: | :---: | :---: |
| [![kpi](docs/assets/charts/kpi.svg)](examples/charts/kpi.json) | [![gauge](docs/assets/charts/gauge.svg)](examples/charts/gauge.json) | [![bar](docs/assets/charts/bar.svg)](examples/charts/bar.json) |
| Scalar aggregate | Explicit target and range | Categorical comparison |

| **horizontal_bar** | **grouped_bar** | **stacked_bar** |
| :---: | :---: | :---: |
| [![horizontal_bar](docs/assets/charts/horizontal_bar.svg)](examples/charts/horizontal_bar.json) | [![grouped_bar](docs/assets/charts/grouped_bar.svg)](examples/charts/grouped_bar.json) | [![stacked_bar](docs/assets/charts/stacked_bar.svg)](examples/charts/stacked_bar.json) |
| Ordered ranking | Compare averages without stacking | Additive disjoint segments |

| **waterfall** | **line** | **area** |
| :---: | :---: | :---: |
| [![waterfall](docs/assets/charts/waterfall.svg)](examples/charts/waterfall.json) | [![line](docs/assets/charts/line.svg)](examples/charts/line.json) | [![area](docs/assets/charts/area.svg)](examples/charts/area.json) |
| Ordered reconciled changes | Ordered temporal trend | Magnitude with zero baseline |

| **stacked_area** | **combo_dual_axis** | **donut** |
| :---: | :---: | :---: |
| [![stacked_area](docs/assets/charts/stacked_area.svg)](examples/charts/stacked_area.json) | [![combo_dual_axis](docs/assets/charts/combo_dual_axis.svg)](examples/charts/combo_dual_axis.json) | [![donut](docs/assets/charts/donut.svg)](examples/charts/donut.json) |
| Aligned additive series | Two explicit units and scales | Exclusive positive total |

| **treemap** | **sunburst** | **scatter** |
| :---: | :---: | :---: |
| [![treemap](docs/assets/charts/treemap.svg)](examples/charts/treemap.json) | [![sunburst](docs/assets/charts/sunburst.svg)](examples/charts/sunburst.json) | [![scatter](docs/assets/charts/scatter.svg)](examples/charts/scatter.json) |
| Validated hierarchy | Nested proportional hierarchy | Paired quantitative values |

| **bubble** | **heatmap** | **histogram** |
| :---: | :---: | :---: |
| [![bubble](docs/assets/charts/bubble.svg)](examples/charts/bubble.json) | [![heatmap](docs/assets/charts/heatmap.svg)](examples/charts/heatmap.json) | [![histogram](docs/assets/charts/histogram.svg)](examples/charts/histogram.json) |
| Third measure mapped to area | Two discrete dimensions | Equal-width ordered bins |

| **boxplot** | **violin** | **table** |
| :---: | :---: | :---: |
| [![boxplot](docs/assets/charts/boxplot.svg)](examples/charts/boxplot.json) | [![violin](docs/assets/charts/violin.svg)](examples/charts/violin.json) | [![table](docs/assets/charts/table.svg)](examples/charts/table.json) |
| Five-number summary | Sample density with Gaussian KDE | Detail or fallback |

## Example

```sql
SELECT category,SUM(amount) AS value FROM sales GROUP BY category;
```

```json
[
  {
    "category": "A",
    "value": 40
  },
  {
    "category": "B",
    "value": 65
  },
  {
    "category": "C",
    "value": 30
  },
  {
    "category": "D",
    "value": 50
  }
]
```

Expected output, not executed: `{"chartType":"bar"}`.

## Architecture

```mermaid
flowchart LR
 SQL --> F[Features]
 Rows --> F
 F --> M[ONNX 10 base classes]
 M --> S[Semantic resolver]
 S --> V[Semantic validation]
 V --> O[21 outputs]
```

## SDKs: intended interfaces

Proposed APIs, not yet verified or published.

```python
from sqltoviz import analyze_query
plan = analyze_query(sql=sql, rows=rows)
```

```typescript
import { analyzeQuery } from '@sqltoviz/core';
const plan = await analyzeQuery({ sql, rows });
```

```csharp
using SqlToViz;
using var engine = new VizEngine();
var plan = engine.Analyze(sql, rows);
```

## Semantic safety

Do not stack averages without valid recomposition. Do not sum COUNT DISTINCT without proven disjointness. Gauge requires a target; boxplot requires quantiles or samples. [Spec](spec/chart-taxonomy-v1.md).

## Research and benchmarks

MAD, period shift, Pareto and Pearson planned. Evaluation targets: macro-F1, coverage, semantic violations and p50/p99 latency. No measured results or published preprint.

[Kaggle](research/kaggle/README.md) · [Paper](research/paper/README.md)

## Progress and contribution

[Roadmap](docs/roadmap.md) · [Issues](https://github.com/jmmana/sqltoviz/issues) · [Contributing](CONTRIBUTING.md)

Apache-2.0 planned; license text pending.
