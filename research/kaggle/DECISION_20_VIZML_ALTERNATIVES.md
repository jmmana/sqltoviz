# Decision: dataset strategy without VizML (E01-02, #20)

Date: 2026-11-27. Authorized by the project owner: do not block the epic on VizML; use verified public sources and synthetic data; document scientific implications.

## Why VizML is excluded (verified, see DATASET_LICENSE_AUDIT.md)
No declared license and all S3 artifacts return HTTP 403 (upstream issues #4, #6). It cannot be acquired reproducibly nor checksummed. It may be added later only with a working checksummed source and written redistribution terms; the pipeline is built so a source can be added without code changes (`sources` registry, one license namespace per source).

## Alternatives evaluated
| Candidate | Finding (measured today) | Decision |
|---|---|---|
| **nvBench** (TsinghuaDatabaseGroup) | README declares MIT; no LICENSE file (GitHub API `license: null`). `NVBench.json` SHA256 `8c85a945…efbcf` (raw, 2026-11-27). 7,247 visualizations on Spider databases: Bar 5523, Pie 520, Line 380, Stacked Bar 359, Scatter 264, Grouping Scatter 129, Grouping Line 72. | **Secondary, evaluation/auxiliary source.** Downloaded locally by script, never redistributed; derived rows live in their own license namespace. Underlying DBs are Spider (CC BY-SA 4.0). |
| Hugging Face `plotly_*_chart` sets | Image datasets, no license declared; not data→chart supervision | Rejected |
| Kaggle search "vizml"/"plotly community feed" | no equivalent | Rejected |
| Spider / BIRD SQL + databases | CC BY-SA 4.0 | **Primary SQL+data substrate** (queries/tables); chart labels come from independent annotation (#24) |
| TPC-H / TPC-DS | EULA 2.2.0; generated locally | Substrate for large analytic schemas (#22) |
| Synthetic generator | own code, Apache-2.0 | **Primary label-controlled source** (#25), built so the SQL text cannot reveal the label |

## Scientific implications (stated, not hidden)
1. **Class coverage.** nvBench covers only bar, stacked bar, pie/donut, line, scatter → 5 of the 10 base classes. kpi, horizontal_bar, area, heatmap and table have no human-labeled public source; their labels come from rule-independent annotation (#24) and synthetic data, so those classes' metrics measure agreement with *our annotation protocol*, not human preference. Reported per class with support.
2. **Imbalance.** nvBench is 76% Bar. Training uses class-weighted loss/stratified group splits; macro-F1 is primary; majority baseline reported.
3. **Label semantics.** nvBench labels reflect the chart requested in natural language, not the "best" chart. We report it as such.
4. **No VizML comparison.** No claim of reproducing or beating VizML. Any related-work comparison is qualitative (E08).
5. **Domain shift.** Spider/BIRD/TPC-derived tables are far smaller/cleaner than the Plotly community corpus; generalization to messy real data is a stated limitation.

## Licensing separation
`data/<namespace>/` per source: `cc-by-sa-4.0/` (Spider, BIRD, derivatives), `mit-readme-declared/` (nvBench derivatives, local only), `tpc-eula/` (local only), `apache-2.0/` (synthetic, annotations). A mixed training table is never published; only per-namespace artifacts with manifests (#30).
