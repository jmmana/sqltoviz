<p align="center"><picture><source media="(prefers-color-scheme: dark)" srcset="docs/assets/logo-dark.svg"><img src="docs/assets/logo-light.svg" width="280" alt="SqlToViz"></picture></p>
<p align="center"><img src="docs/assets/hero-es.svg" width="100%" alt="SqlToViz — 21 visualizaciones"></p>

<p align="center"><a href="README.md">English</a> · <a href="README.es.md">Español</a> · <a href="docs/roadmap.md">Roadmap</a> · <a href="spec/chart-taxonomy-v1.md">SqlVizSpec</a></p>

![Pre-alpha](https://img.shields.io/badge/status-pre--alpha-818cf8) ![Python](https://img.shields.io/badge/Python-planned-3776AB) ![TypeScript](https://img.shields.io/badge/TypeScript-planned-3178C6) ![.NET](https://img.shields.io/badge/.NET-8%20%7C%2010-512BD4)

> **Pre-alfa: imágenes ilustrativas, no ejecuciones del SDK. Modelo, paquetes y playground pendientes.**

## Qué es SqlToViz

Proyecto de recomendación visual a partir de SQL y filas resultantes, con inferencia ONNX local y validación semántica determinista.

## Galería de 21 visualizaciones

Cada imagen enlaza al fixture con SQL, filas sintéticas, metadatos, salida esperada y explicación.

| **kpi** | **gauge** | **bar** |
| :---: | :---: | :---: |
| [![kpi](docs/assets/charts/kpi.svg)](examples/charts/kpi.json) | [![gauge](docs/assets/charts/gauge.svg)](examples/charts/gauge.json) | [![bar](docs/assets/charts/bar.svg)](examples/charts/bar.json) |
| Agregado escalar | Objetivo y rango explícitos | Comparación categórica |

| **horizontal_bar** | **grouped_bar** | **stacked_bar** |
| :---: | :---: | :---: |
| [![horizontal_bar](docs/assets/charts/horizontal_bar.svg)](examples/charts/horizontal_bar.json) | [![grouped_bar](docs/assets/charts/grouped_bar.svg)](examples/charts/grouped_bar.json) | [![stacked_bar](docs/assets/charts/stacked_bar.svg)](examples/charts/stacked_bar.json) |
| Ranking ordenado | Comparar promedios sin apilar | Segmentos aditivos disjuntos |

| **waterfall** | **line** | **area** |
| :---: | :---: | :---: |
| [![waterfall](docs/assets/charts/waterfall.svg)](examples/charts/waterfall.json) | [![line](docs/assets/charts/line.svg)](examples/charts/line.json) | [![area](docs/assets/charts/area.svg)](examples/charts/area.json) |
| Variaciones ordenadas conciliables | Tendencia temporal ordenada | Magnitud con base cero |

| **stacked_area** | **combo_dual_axis** | **donut** |
| :---: | :---: | :---: |
| [![stacked_area](docs/assets/charts/stacked_area.svg)](examples/charts/stacked_area.json) | [![combo_dual_axis](docs/assets/charts/combo_dual_axis.svg)](examples/charts/combo_dual_axis.json) | [![donut](docs/assets/charts/donut.svg)](examples/charts/donut.json) |
| Series aditivas alineadas | Dos unidades y escalas explícitas | Partes exclusivas y total positivo |

| **treemap** | **sunburst** | **scatter** |
| :---: | :---: | :---: |
| [![treemap](docs/assets/charts/treemap.svg)](examples/charts/treemap.json) | [![sunburst](docs/assets/charts/sunburst.svg)](examples/charts/sunburst.json) | [![scatter](docs/assets/charts/scatter.svg)](examples/charts/scatter.json) |
| Jerarquía validada | Jerarquía proporcional anidada | Valores cuantitativos pareados |

| **bubble** | **heatmap** | **histogram** |
| :---: | :---: | :---: |
| [![bubble](docs/assets/charts/bubble.svg)](examples/charts/bubble.json) | [![heatmap](docs/assets/charts/heatmap.svg)](examples/charts/heatmap.json) | [![histogram](docs/assets/charts/histogram.svg)](examples/charts/histogram.json) |
| Tercera métrica en área | Dos dimensiones discretas | Intervalos ordenados de igual ancho |

| **boxplot** | **violin** | **table** |
| :---: | :---: | :---: |
| [![boxplot](docs/assets/charts/boxplot.svg)](examples/charts/boxplot.json) | [![violin](docs/assets/charts/violin.svg)](examples/charts/violin.json) | [![table](docs/assets/charts/table.svg)](examples/charts/table.json) |
| Resumen de cinco números | Densidad muestral con KDE gaussiana | Detalle o respaldo |

## Ejemplo

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

Salida esperada, no ejecutada: `{"chartType":"bar"}`.

## Arquitectura

```mermaid
flowchart LR
 SQL --> F[Features]
 Rows --> F
 F --> M[ONNX 10 base classes]
 M --> S[Semantic resolver]
 S --> V[Semantic validation]
 V --> O[21 outputs]
```

## SDK: interfaces previstas

APIs propuestas, aún no verificadas ni publicadas.

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

## Seguridad semántica

No apilar promedios sin recomposición válida. No sumar COUNT DISTINCT sin disjunción demostrada. Gauge exige objetivo; boxplot exige cuantiles o muestras. [Spec](spec/chart-taxonomy-v1.md).

## Investigación y benchmarks

MAD, cambio temporal, Pareto y Pearson planificados. Se evaluarán Macro-F1, cobertura, violaciones semánticas y latencia p50/p99. No hay resultados medidos ni preprint publicado.

[Kaggle](research/kaggle/README.md) · [Paper](research/paper/README.md)

## Progreso y contribución

[Roadmap](docs/roadmap.md) · [Issues](https://github.com/jmmana/sqltoviz/issues) · [Contributing](CONTRIBUTING.md)

Licencia prevista Apache-2.0; texto pendiente.
