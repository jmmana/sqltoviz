# luo2021nvbench (Luo et al., SIGMOD 2021)
Full text read: SIGMOD'21 camera-ready (13 pages). Also read the 5-page arXiv summary (2112.12926) and the repository README.

## Source
Paper: https://dbgroup.cs.tsinghua.edu.cn/ligl/papers/sigmod21-nvbench.pdf (DOI 10.1145/3448016.3457261). Secondary: https://arxiv.org/pdf/2112.12926v1 (titled "nvBench: A Large-Scale Synthesized Dataset for Cross-Domain NL2VIS Task", 5 pages, abbreviated). README: github.com/TsinghuaDatabaseGroup/nvBench. Numbers below are from the SIGMOD paper unless marked.

## Problem formulation
No NL2VIS benchmark existed (Abstract). Synthesize (NL, VIS) pairs from (NL, SQL) pairs, because SQL says what data is needed and a VIS query additionally says how to visualize (Sect. 1, 2.1).

## Input and output
Synthesizer input: one (NL, SQL) pair; output: several (NL, VIS) pairs (Sect. 2.1). Model task (seq2vis): NL query + table schema -> VIS query token sequence (Sect. 4.1).

## Data (source, size, license/availability as stated)
Built on Spider (200 DBs, 138 domains, 10,181 (NL, SQL) pairs; Sect. 3.1). nvBench: 153 databases, 780 tables, 105 domains, 4,017 columns, 1,000,572 rows; columns 68.78% categorical, 11.58% temporal, 19.64% quantitative; 7,247 visualizations, 25,750 (NL, VIS) pairs (Tables 2, 3). Avg 3.746 NL per VIS; avg 22.29 words per NL (Table 3).
Licence: the paper states none beyond the ACM copyright notice. The README states "nvBench is available under the MIT license". The GitHub API returned license = null for the repository (checked 2026-11-27), so no LICENSE file is registered.

## Method
Chart-type labels and VQL/SQL relationship (exact): a shared AST grammar extends SemQL: "Root ::= Q | Visualize Q", with "Visualize ::= bar | pie | line | scatter | stacked bar | grouping line | grouping scatter" (Fig. 5, Sect. 2.2). A VIS tree is an SQL tree edited by deletions (only Select and Order subtrees; attributes enumerated as 1, 2 or 3 columns) and insertions (grouping/binning plus an aggregate node, a Visualize subtree, Order) (Sect. 2.3). Filter, Superlative and group subtrees are kept unchanged ("Invariant (what data)"; "Variant (how to visualize)", Sect. 2.1). Chart types allowed per column-type combination come from rules of thumb (Table 1), e.g. T+Q: grouping/binning/none + agg -> {bar, pie, line}; Q+Q -> scatter; T+Q+C -> {grouping line, stacked bar}. So one SQL query yields several candidate chart types; a gold label is a synthesized candidate, not a human-chosen "best" chart. Candidates are pruned by DeepEye, a classifier trained on 2520/30892 labeled good/bad charts (Sect. 2.4). README fields: chart in {Bar, Pie, Line, Scatter, Stacked Bar, Grouping Line, Grouping Scatter}; vis_query.VQL is the string "Visualize <TYPE> <SQL>" (README example: "Visualize PIE SELECT Rank , COUNT(Rank) FROM Faculty GROUP BY Rank"); also vis_obj, hardness, nl_queries.
NL: rule-based insertions (phrases from Tableau Ask Data and NL4DV), back-translation smoothing; for tree deletions NL was manually rewritten by two PhD students: 1,838 vis objects (25.36%), 3,500 NL variants (13.59%) (Sects. 2.5, 3.1). Rendering: Vega-Lite and ECharts (Sect. 2.6).

## Evaluation protocol (splits, metrics, baselines)
Human validation: 23 experts, 312 crowd workers (appen), ~10% sample plus 100 handwritten NL (Sect. 3.3). seq2vis (bi-LSTM + attention/copy) random split 20,598 train / 1,162 val / 3,990 test (Sect. 4.2). Metrics: vis tree matching, vis result matching, component matching. Baselines: NL4DV, DeepEye (Sect. 4.2).

## Key reported results (exact numbers with location)
- NL-VIS match rated 4-5: experts 86.9%, crowd 88.7% (Sect. 3.3, Exp-T2). NL "handwritten-like": crowd 85.6%, experts 81.1% (Exp-T1).
- ~2% imperfect NL revised -> nvBench* (Sect. 1); 231 low-rated pairs (Sect. 4.5).
- Man-hours 5.7% of from-scratch (~2.4 days vs ~42 days) (Sect. 3.3).
- seq2vis with attention: 65.69% tree accuracy (Sect. 4.3); Table 5 Overall: DeepEye top-1 9.1%, top-3 13.1%, top-6 15.9%, all 22.2%; NL4DV 13.7%; seq2vis 65.7%.
- Bar 76.21% of VIS, pie 7.18%, line 5.24%, scatter 3.67% (Table 3).

## Stated limitations
Seq2vis does not predict values V; a heuristic fills them (~92.3% accuracy) (Sect. 4.2). NL4DV cannot handle join/nested; DeepEye cannot handle join, nested, filter (Sect. 4.2). Experts rarely specify (extra) hard cases by NL (Sect. 3.3). Only seven chart types; the arXiv summary lists heatmap/box-plot, conversational NL2VIS and domain-specific data as future work (arXiv Sect. 5-6). No dedicated limitations section in the SIGMOD paper.

## Code/data availability (as stated)
"The code and benchmark is available at https://github.com/TsinghuaDatabaseGroup/nvBench" (Sect. 1). Repo: nvBench.json, nvBench_VegaLite, database/.

## Relevance to a system that recommends charts from a SQL query + its result set (Reviewer note)
- Reviewer note: nvBench is the only one of the four with SQL-paired charts (VQL embeds the SQL), so each example gives a query, a result and a chart type; usable as supervision for chart-type choice.
- Reviewer note: but the input is an NL question, and gold charts are valid candidates after DeepEye filtering, not unique ground truth.

## Comparability issues
- Reviewer note: internal inconsistencies across versions: arXiv abstract says 750 tables, its text and SIGMOD say 780; arXiv Fig. 3 lists scatter = 226 VIS and total 7247 (the rows sum to 7,207), SIGMOD Table 3 lists 266; ncNet and arXiv text say 7,274 visualizations, SIGMOD says 7,247; arXiv says "300+" crowd workers, SIGMOD 312. Cite SIGMOD figures.
- Reviewer note: the 65.7% accuracy is an exact tree match on NL input, with schema given; not a chart-type accuracy.
- Reviewer note: the label distribution is dominated by bar (76% of VIS), so a majority-class baseline is strong.
