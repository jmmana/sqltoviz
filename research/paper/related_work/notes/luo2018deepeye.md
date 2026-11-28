# Luo et al. 2018 - DeepEye: Towards Automatic Data Visualization (ICDE 2018, DOI 10.1109/ICDE.2018.00019)

## Source
Author-hosted PDF, https://dbgroup.cs.tsinghua.edu.cn/ligl/papers/icde18-deepeye.pdf (10 pages, ICDE 2018 camera-ready, pp. 101-112). Full text read (all sections I-VIII; Tables VI-VIII and Figs 10-12 only partly via text extraction).

## Problem formulation
Given a relational table D with m columns, (1) visualization recognition: is a given visualization good or bad; (2) ranking: which of two is better; (3) selection: find top-k visualizations (Abstract, Sec. I). Authors say they focus on (3).

## Input and output
Input: one table D (Sec. II-A). Output: top-k visualizations. Each is a query in a small language: VISUALIZE {bar,pie,line,scatter}, SELECT X',Y', FROM D, optional TRANSFORM (BIN/GROUP), ORDER BY (Fig. 2). Two-column case is the main one; one-column and multi-column are described as "easily extended" (Sec. II-B).

## Data (if any; source, size, availability as stated)
42 real-world datasets (real estate, social study, transportation); tuples 3 to 99527, average 3381; columns 2 to 25 (Sec. VI, Table III). 32 for training, 10 for test (Table IV: e.g. FlyDelay 99,527 tuples, 6 columns). 9 further "real use case" datasets D1-D9 from websites (Table V). Availability of the datasets/labels: no statement found.

## Method
- Search space: 528 m(m-1) visualizations for two columns (Sec. II-B); 264 m for one column; 704 m^3 for three columns.
- Features: distinct count, tuple count, unique ratio, max/min, data type (Cat/Num/Tem), column correlation, chart type; 14 features for two columns (Sec. III).
- Recognition: binary decision tree; Bayes and SVM also tested (Sec. III, VI-B).
- Ranking: LambdaMART learning-to-rank (Sec. III); expert-rule partial orders over three factors (matching quality of data and chart, quality of transformation, column importance), Hasse-diagram top-k (Sec. IV); hybrid of the two.
- Rules from [12] (Show Me) and [13] (Mackinlay 1986) are adopted for same-data comparisons, e.g. pie/bar for categorical X, bar preferred if AVG or >=10 categories, pie not applicable if min(Y)<0 (Sec. IV-A).
- Optimizations: rule-based pruning of candidates, shared grouping/binning, postponed sorting (Sec. V, VI).

## Evaluation protocol (if any)
Ground truth: 100 students labelled all candidate charts good/bad and compared good pairs; 2520/30892 good/bad charts and 285,236 pairwise comparisons (Sec. VI). Train 32 / test 10 datasets; "cross validation ... similar results" (no numbers). Metrics: precision/recall/F-measure (recognition), NDCG (ranking), running time. Environment: MacBook Pro, 8 GB RAM, 2.9 GHz Core i5.

## Key reported results (exact numbers with location)
- Decision tree "averagely 95% F-measure" (Sec. VI-B, Fig. 10); DT better than SVM and Bayes (Table VII, VIII).
- NDCG, partial order: max 0.97, min 0.81; learning-to-rank: max 0.85, min 0.52 (Sec. VI-C, Fig. 11a).
- Hybrid average NDCG 0.94, better than learning-to-rank by 32.4% and partial order by 6.8% (Sec. VI-C).
- Coverage: for D1, 5 practically used charts are covered by top-23 results (Sec. VI-A, Table VI); on D3 all 4 website charts appear on first page (top-6) (Fig. 9).
- Runtime: one example bar is 550 ms (20% enumeration, 80% selection) (Sec. VI-D, Fig. 12); authors state "complete in seconds for datasets with reasonable size".

## Stated limitations
- Only four chart types (bar, line, pie, scatter), chosen from a survey [6] (34%, 23%, 13% for bar, line, pie) (Sec. II-B).
- Future work named: keyword queries for user intent (Sec. VIII).
- Authors note that ML black boxes may not capture perception for lack of examples and are hard to speed up (Sec. III remarks).

## Code/data availability (as stated)
No code or dataset link found in the text. A screenshot of the DeepEye UI is shown (Fig. 9).

## Relevance to a system that recommends charts from a SQL query + its result set (Reviewer note)
Closest in spirit: it takes a table and enumerates BIN/GROUP/AGG/ORDER transformations that are SQL-like. Differences: DeepEye enumerates transformations itself, whereas a query-driven system receives an already aggregated result set and only chooses the encoding. Its type-based rules (pie not for AVG or negative values, many categories favour bar) are reusable ideas. Its features (cardinality, type, correlation) are computable from a result set.

## Comparability issues
- Ground truth is from 100 students on 42 datasets; labels not stated as released, so numbers cannot be reproduced.
- NDCG/F-measure are per-dataset averages over 10 test tables from the same label pool; no variance reported in the text I read.
- Evaluation is on raw tables, not on query results; no SQL or natural-language input.
- Reviewer note: the 95% F-measure is for a good/bad classification where good charts are 2520 of 33412 labelled (about 7.5%, computed by me), so a majority-class baseline is not reported by the authors.
