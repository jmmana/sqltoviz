# Zhou et al., Table2Charts (arXiv 2008.11015)
Full text read (PDF via arxiv.org, pdftotext, including appendix A/B). Tables 2-4 were read from the layout-preserving extraction. Some section numbers are inferred from heading order in the extraction and may be off by one subsection.

## Source
https://arxiv.org/pdf/2008.11015, version v4 (cs.DB, 28 Jun 2021). Published as KDD '21, Aug 14-18, 2021, DOI 10.1145/3447548.3467279. Authors from Microsoft Research Asia and interns (Xi'an Jiaotong, Peking, Tsinghua, NYU).

## Problem formulation
- Chart recommendation as table-to-sequence generation: fill chart grammar templates with action tokens (field tokens plus command tokens: chart type, [SEP], [Cluster]/[Stack]) (Sec. 2). Covers both "data queries" (which fields) and "design choices" (chart type, field-to-axis mapping, bar grouping).
- Two tasks: multi-type (ranked list over major types) and single-type (given a chart type, fill details); six chart types: line, bar, scatter, pie (major), area, radar (minor) (Sec. 2.1).
- Scope restriction stated: whole fields only, no filtering, aggregation, bucketing or ordering (Sec. 2.1).

## Input and output
- Input: a table (n fields, each with header name and values) (Sec. 2.1). Token features: FastText header embedding, categories (token/field type), data statistics/distribution features (Sec. 3.1, App. A.2).
- Output: ranked action sequences, e.g. "[Bar](Total Male Students)(Total Female Students)[SEP](Program)[Stack]" (Sec. 2.1).

## Data (source, size, license/availability as stated)
- Excel corpus (built by the authors from spreadsheets crawled from the public web): 266,252 charts in 165,214 unique tables, 98,588 schemas; type counts: 113,390 line (42.59%), 67,600 bar (25.39%), 64,934 scatter (24.39%), 17,436 pie (6.55%), 1,990 area (0.75%), 902 radar (0.34%) (Sec. 4.1.1). Allocation by schema 7:1:2 (train/val/test).
- Plotly corpus (VizML's public corpus) used for testing only: 36,888 tables, 67,617 charts (22,644 line, 20,053 scatter, 24,204 bar, 716 pie) (Sec. 4.1.2).
- Human evaluation: 500 web tables chosen by query frequency from a search engine (Sec. 4.2.3).
- No license statement for the Excel corpus found; the text does not say it is released.

## Method
- Encoder-decoder deep Q-network with copying mechanism (customized CopyNet; bidirectional GRU encoder, unidirectional GRU decoder), Q(s,a) trained with search sampling to reduce exposure bias; beam search at inference (beam size 4, expand limit 100, App. B.1.1).
- Mix-and-transfer: train one mixed model on major types (used for the multi-type task), freeze its encoder, train a new decoder per single-type task (Sec. 3.3).
- Hard constraints only on field type and field count (Sec. 2.2). Parameters: encoder 1.3M, decoder 0.5M (Sec. 4.3).

## Evaluation protocol (splits, metrics, baselines)
- Metric: recall at top-k (R@1, R@3), computed at three stages (data queries, design choices, overall) by matching against user-created charts (Sec. 4.2.2, App. B.2.1); human ratings 1-5 for top-1 charts by 10 experts, 3 experts per table, Wilcoxon signed-rank test (Sec. 4.2.3). Results averaged over 5 runs.
- Baselines: DeepEye (public ML model, not retrained), Data2Vis (retrained on the Excel training set, 180,383 samples), DracoLearn (default rules, no training), VizML (retrained, design choices only) (Sec. 4.2.1, App. B.1.2).
- Excel numbers are on the held-out test split; Plotly numbers are on the whole sampled Plotly set without training on it.

## Key reported results (exact numbers with location)
- Table 2, Excel (R@1 / R@3): Data queries: DeepEye 34.33/47.13, Data2Vis 31.16/42.18, Table2Charts 64.96/77.88. Design choices: DeepEye 17.83/20.35, Data2Vis 26.26/48.88, VizML 21.38 (R@1 only), Table2Charts 57.69/77.59. Overall: DeepEye 10.18/15.85, Data2Vis 13.17/27.14, Table2Charts 43.84/61.84.
- Table 2, Plotly (R@1 / R@3): Data queries: DeepEye 49.99/62.80, Data2Vis 63.78/71.82, Table2Charts 83.34/92.02. Design choices: DeepEye 37.69/37.70, Data2Vis 13.15/32.85, VizML 30.21, Table2Charts 40.17/55.57. Overall: DeepEye 25.05/35.98, Data2Vis 16.42/33.96, Table2Charts 33.37/48.03.
- Sec. 4.2.2: DracoLearn "R@1 < 1% on all stages".
- Table 3 (330 tables after filtering unsuitable; ratings 5/4/3/2/1, avg): Table2Charts 517/158/115/102/98, 3.90; Data2Vis 309/178/167/125/211, 3.25; DeepEye 312/166/139/137/236, 3.18. Wilcoxon p < 0.0001 vs DeepEye and vs Data2Vis (Sec. 4.2.3).
- Sec. 4.2.4: 12.14 ms per table for Table2Charts vs 48.19 ms DeepEye, 210 ms Data2Vis.
- Table 4 single-type (R@1 / R@3, Separate vs Mixed vs Transfer), e.g. Line 52.02/68.28, 52.53/68.58, 53.78/69.37; Bar Transfer 60.25/73.14; Pie Transfer 79.72/94.04; Area Separate 27.48/40.32, Transfer 49.30/59.99; Radar Separate 49.90/60.93, Transfer 71.77/77.00.
- Sec. 4.3: Separate has 10.8M parameters vs Transfer 4.3M.

## Stated limitations
- Only simple charts; combo charts left to future work (Sec. 4.1.1). No filtering, aggregation, bucketing, ordering; < 5% of charts in training data customize them (Sec. 2.1).
- Multi-type model "may lack diversity" (all top-3 for the example were bar charts); mixing single- and multi-type results is future work (Sec. 4.4).
- Precision cannot be computed from the corpora because "there can be good charts not created by users" (Sec. 4.2 footnote 9). Deciding table suitability for charting is out of scope (footnote 11).
- Code "will be published" after internal review (footnote 1).

## Code/data availability (as stated)
- Footnote 1: "Code will be published at https://github.com/microsoft/Table2Charts ... once it is approved by an internal review." The Excel corpus release is not stated.

## Relevance to a system that recommends charts from a SQL query + its result set (Reviewer note)
- Reviewer note: input is a table, matching a result set, and it recommends field mapping and chart type; the field-selection stage is largely fixed by the query when the result set is given. No SQL or natural-language input.
- Reviewer note: it has no aggregation/transformation modeling, which matters because SQL results are often already aggregated.

## Comparability issues
- Reviewer note: recall is defined by exact match to user-created charts of a table (a table with several charts counts as recalled if any one matches); not comparable to accuracy per design choice (VizML) or to rating-based scores.
- Reviewer note: baselines are heterogeneous (DeepEye and DracoLearn not retrained, Data2Vis retrained, VizML design choices only with R@1 only); DeepEye ground truth was modified (grouping/binning charts dropped, App. B.2.2).
- Reviewer note: the Excel corpus and the Plotly set are deduplicated differently from VizML's; Excel is the authors' own data.
