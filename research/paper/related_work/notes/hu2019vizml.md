# Hu et al., VizML (arXiv 1808.04819)
Full text read (PDF via arxiv.org, text extracted with pdftotext). Section numbers below are the paper's. Some section numbers are inferred from heading order in the extraction and may be off by one subsection.

## Source
https://arxiv.org/pdf/1808.04819, version v1 (cs.HC, 14 Aug 2018). Authors: Hu, Bakker, Li, Kraska, Hidalgo (MIT). Paper is IEEE-VIS-style; the PDF has no venue stated in the text read.

## Problem formulation
- Visualization recommendation is framed as predicting "design choices" (higher-level choices that bundle lower-level encodings) from a dataset (Sec. 2, 2.1, 2.2). Each design choice c gets its own model G_c approximating an ideal F_c; models are trained independently and without contextual factors (Sec. 2.2).
- Scope: visual-encoding choices only; data-query selection (column choice) and column transformation/aggregation are NOT modeled because >90% of Plotly charts use all columns and only 0.16% of 13,321,598 traces have transformations (Sec. 4.1/Sec. 3).

## Input and output
- Input: hand-engineered features: 81 single-column, 30 pairwise-column, 841 dataset-level features (aggregations with 16 functions) (Sec. 4.3, Table 4).
- Output: one class per task. Tasks: Visualization Type (VT, 2/3/6-class), Has Shared Axis (HSA, 2-class), Mark Type (MT, 2/3/6-class), Is Shared X/Y axis (ISA, 2-class), Is on X or Y axis (XY, 2-class) (Sec. 6.1). 2-class = line vs bar; 3-class = scatter vs line vs bar. Total 7 prediction tasks reported in Table 2.

## Data (source, size, license/availability as stated)
- Plotly Community Feed via Plotly API, 2015-07-17 to 2018-01-06; 2,359,175 visualizations collected, 2,102,121 with all three config objects, 1,989,068 parsed (Sec. 4.1).
- 143,007 unique users (Sec. 4.1). Exact dedup: 1,066,443 datasets, 2,884,437 columns; after keeping one dataset per user: 119,815 datasets and 287,416 columns (Sec. 5.1).
- Rows per dataset: mean 3105.97, median 30, max 10x10^6; columns: 94.97% <= 25 (Sec. 4.2).
- No license statement found in the text. Acknowledgments thank Plotly "for making the Community Feed data available".

## Method
- Primary model: fully connected NN, 3 hidden layers of 1,000 ReLU units; Adam, batch 200, lr 5e-4 with plateau decay, max 100 epochs (Sec. 6.1). PyTorch.
- Baselines: naive Bayes, KNN (k=5), logistic regression (L1), random forest, scikit-learn defaults (Sec. 6.1).
- Feature sets added incrementally: D, D+T, D+T+V, D+T+V+N (dimensions, types, values, names). Baselines use All only.
- Class balancing by oversampling train/val/test to majority size (Sec. 6.1).

## Evaluation protocol (splits, metrics, baselines)
- Text states 60/20/20 train/validation/test for NN, and also that results are the average of 5-fold cross-validation, each sample in exactly one test set (Sec. 6.1). Metric: accuracy (Sec. 6.1).
- Crowdsourced benchmark (Sec. 8): 99 Plotly datasets (33 bar, 33 line, 33 scatter), each rendered as bar/line/scatter; MTurk workers (150 completed the two-class experiment, 150 separate workers the three-class); each worker rated 30 datasets; mean 68.18 evaluations per dataset in the 66-dataset set. Metric: Consensus-Adjusted Recommendation Score (CARS), 95% CIs from 10^5 bootstraps.
- Compared predictors: VizML, Plotly users, single MTurk, DeepEye, Data2Vis, random.

## Key reported results (exact numbers with location)
- Table 2 (NN, All features): VT C=2 86.0, C=3 79.4, C=6 89.4; HSA 97.3; MT C=2 84.9, C=3 67.8, C=6 82.9; ISA 98.3; XY 83.1. SEM < 0.1% for all.
- Table 2 baselines (All): VT C=2: NB 63.4, KNN 76.5, LR 81.8, RF 81.2. MT C=2: NB 57.6, KNN 72.4, LR 73.6, RF 78.3. XY: NB 70.0, KNN 65.6, LR 79.1, RF 83.4.
- Table 2 Nraw (thousands): VT 42.2/87.0/99.3, HSA 119; MT 94.7/163/183, ISA 287, XY 287.
- Fig. 12a (two-class CARS): VizML 88.96 +- 1.66; MTurk 86.66 +- 5.38; Plotly 90.35 +- 1.85; Data2Vis 75.61 +- 2.44; DeepEye 79.12 +- 4.33; random 74.30 +- 7.09; minimum 48.61 +- 2.95 (Sec. 8.4).
- Fig. 12b (three-class CARS): VizML 81.18 +- 2.39; MTurk 79.28 +- 4.66; Plotly 79.58 +- 2.44; Data2Vis 64.75 +- 3.13; DeepEye 68.09 +- 4.11; random 60.37 +- 6.98; minimum 26.93 +- 3.46.
- Intro says NN accuracy "~70-95%" on design choices.

## Stated limitations
- Bias toward the Plotly corpus (user, system, dataset level) despite deduplication; neither Plotly users nor MTurkers are visualization experts; only a subset of the recommendation pipeline is covered; no user-facing application built (Sec. 9, 3).
- Independent per-choice predictions may be incompatible; end-to-end combination left to future work (Sec. 2.2, 10).
- DeepEye and Data2Vis "were not trained to perform visualization type prediction" (Sec. 8.4); both humans in the benchmark saw more information (cleaned/renamed columns) than the model (Sec. 8.2).

## Code/data availability (as stated)
- No code or corpus release statement found in the text. The paper calls for "public training and benchmarking corpuses" as future work (Sec. 10).

## Relevance to a system that recommends charts from a SQL query + its result set (Reviewer note)
- Reviewer note: input (a tabular dataset of columns) matches a result set; features are computed from values/types/names, which are available from a query result. VizML does not use the SQL query, the question, or the schema.
- Reviewer note: outputs are chart type/axis assignment only, restricted to bar/line/scatter in the 2/3-class tasks; no aggregation or encodings beyond those listed.

## Comparability issues
- Reviewer note: Table 2 accuracies are on class-balanced (oversampled) sets, so they are not comparable to unbalanced accuracy or to top-k metrics. Chance is 1/C.
- Reviewer note: text is inconsistent on the number of design choices (abstract "five", intro "seven"; Sec. 6 lists five tasks with multi-class variants, Table 2 has seven columns) and on split (60/20/20 vs 5-fold CV).
- Reviewer note: CARS is a consensus-weighted score with a nonzero floor (min 48.61 / 26.93), not accuracy; benchmark is 66/99 datasets with bar/line/scatter only.
- Reviewer note: training pairs are human-made Plotly charts, so labels reflect observed choices, not verified optimal ones (the paper itself assumes this, Sec. 2.2).
