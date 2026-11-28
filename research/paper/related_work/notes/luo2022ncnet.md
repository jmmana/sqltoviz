# luo2022ncnet (Luo et al., IEEE TVCG 2022, VIS 2021)
Full text read (10 pages) of the authors' preprint.

## Source
https://github.com/Thanksyy/Vega-Zero/blob/main/ncNet-VIS21.pdf (raw copy, also referenced from the ncNet README). Header still shows placeholder DOI/"Manuscript received xx xxx. 201x". No arXiv version found (searched arXiv API and web). Published as TVCG vol. 28, no. 1, pp. 217-226, DOI 10.1109/TVCG.2021.3114848 (per web search results, not the PDF). The qcai.qcri.org copy returned an HTML bot page, not a PDF.

## Problem formulation
NL2VIS as neural machine translation: learn Y = f_theta(X), X = embed(N, C, D), with N an NL query, C an optional chart template, D a tabular dataset (Sect. 4.5).

## Input and output
Input: NL query, one table (CSV/JSON/relational table), optional chart template (Fig. 1, Sect. 4.2). Output: a Vega-Zero sequence (mark, data, encoding, transform), converted by hard-coded code to Vega-Lite or ggplot2 (Sects. 4.3, 5.5). Chart templates: bar, stacked bar, pie, line, grouping line, scatter, grouping scatter, with optional sorting (Fig. 4). Mark values: bar, line, point, arc (Sect. 4.3).

## Data (source, size, license/availability as stated)
nvBench (Sect. 6.2): 153 databases, 780 tables, 105 domains; text says 7,274 visualizations, Fig. 9 lists 7247; 25,750 pairs. Original split 20,598 / 1,162 / 3,990 (Sect. 6.3). After removing join cases and adding the chart-template variant of each pair: 25,238 train / 4,920 test (Sect. 6.3). Spider data needed (README).

## Method
Transformer encoder-decoder, 3 blocks each, 8 heads, embedding 256, input truncated at 512 tokens, Adam lr 0.0005, dropout 0.1, batch 64, ~40 MB model (Sect. 6.1). Input = NL tokens + chart-template tokens with masked slots [X][Y][Z][F][G][B][S][K] + linearized table (Sect. 5.2). Large tables: only cell values similar to NL text values are added (Sect. 5.2). Attention forcing (mask) and visualization-aware beam-search correction (top-5 candidates; column and column-type rules) (Sect. 5.4); the latter "can increase ~3% accuracy".

## Evaluation protocol (splits, metrics, baselines)
Metric: exact match of output Vega-Zero with ground truth, rank-1 only (Sect. 7.3). Baseline: a state-of-the-art NL2SQL neural model [18] adapted to NL2VIS. Variants: ncNet without/with chart template. User study: 4 experts + 2 non-experts, 5 databases, 50 target visualizations (Sect. 7.2). No comparison with NL4DV/FlowSense numbers.

## Key reported results (exact numbers with location)
- Average accuracy 77.8% (no template) and 79.6% (with template); baseline 65.0%; "outperform it by 12.8% and 14.6%" (Sect. 7.3, Fig. 13).
- Join cases about 3.6% lower accuracy than non-join (Sect. 6.3).
- User study: experts better than non-experts; non-expert task time about twice experts'; system response about 1 second (Sect. 7.2, Fig. 12; per-user pass rates only in the figure).
- Error analysis: main failure is columns/transform; chart type/sort errors occur mostly without a template; gold sometimes at rank-k; some Vega-Zero mismatches yield equal charts (Sect. 7.3).

## Stated limitations
(L1) Limited benchmarks (VizNet, nvBench). (L2) Only one-shot NL queries, no conversational input (Sect. 8.1). Conclusion: non-friendly column names ("foo bar") and big data remain to be handled (Sect. 9). Input length limit of 512 tokens (Sects. 5.2, 6.1).

## Code/data availability (as stated)
Code at github.com/Thanksyy/ncNet; Vega-Zero converter at github.com/Thanksyy/Vega-Zero (Sects. 1, 5.5). The README (read via fetch, not in the paper) says "available under the MIT License" and requires Spider downloaded from Google Drive.

## Relevance to a system that recommends charts from a SQL query + its result set (Reviewer note)
- Reviewer note: ncNet needs an NL query; it cannot take a SQL query alone. Closest reusable parts: Vega-Zero output, table linearization, rule-based type checking of predicted columns, top-k recommendation remark (Sect. 5.4.2).
- Reviewer note: chart templates act as a user-supplied chart-type hint; the paper shows chart-type errors drop when one is given.

## Comparability issues
- Reviewer note: 77.8%/79.6% is exact string match on the full Vega-Zero (columns, filters, sort, chart type), not chart-type accuracy; chart-type-only numbers are only in the Fig. 13 heatmaps (text partly garbled in extraction, not quoted).
- Reviewer note: the test set differs from nvBench's: joins removed, template-augmented pairs (4,920 vs 3,990); the template-augmented set duplicates each test pair.
- Reviewer note: the seq2vis 65.7% (nvBench paper) and the NL2SQL-baseline 65.0% (here) use different test sets and metrics.
- Reviewer note: the 7,274 vs 7,247 inconsistency inherited from nvBench arXiv text.
