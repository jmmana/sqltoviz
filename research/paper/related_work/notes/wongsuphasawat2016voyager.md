# Wongsuphasawat et al. 2016 - Voyager (IEEE TVCG 22(1), InfoVis 2015, DOI 10.1109/TVCG.2015.2467191)

## Source
https://idl.cs.washington.edu/files/2015-Voyager-InfoVis.pdf (author-hosted PDF, manuscript dated 1 Aug. 2015 accepted). Full text read.

## Problem formulation
Support breadth-oriented exploratory analysis of unfamiliar tabular data by replacing manual view specification with faceted browsing of automatically recommended charts (Abstract, Sec. 1). Variables, transformations and encodings produce a combinatorial space that must be pruned and ranked.

## Input and output
Input: one relational table (descriptive statistics per variable: cardinality, min, max, std dev, skew) plus user-selected variable set U (Sec. 5.2). Output: gallery of Vega-lite charts, one top-ranked encoding per variable set/transformation, plus expandable alternatives (Sec. 4.2, 5.2).

## Data (if any; source, size, availability as stated)
Scenario: cars, 406 rows, 9 variables (Sec. 3). Study: movies, 3,201 records, 15 variables (7 nominal, 1 temporal, 8 quantitative); birdstrikes (FAA), 10,000 records, 14 variables (8 nominal, 1 geographic, 1 temporal, 4 quantitative) (Sec. 6.1). Availability not stated beyond "real-world".

## Method
- Compass engine, 3 phases (Fig. 9): variable selection (adds exactly one non-selected variable to the k selected), transformation (aggregate/bin; time units by extent), encoding enumeration and ranking (Sec. 5.2).
- Enumeration: variables assigned to permitted channels (Table 1), mark types by required/permitted channels (Table 2) and mark ranking by x/y type (Table 3).
- Ranking: channel effectiveness from Cleveland and Mackinlay, cardinality penalties, penalty for multiple retinal encodings, gallery-readability preferences; weighted sum s(e), "manually tuned" weights (Sec. 5.2).
- Clustering of encoding variants (Table 4); main gallery shows data variation over design variation (C1).
- Show Me [25] is described as "a set of heuristics to aid in the construction of small multiples and recommend chart types"; Voyager extends this by also recommending variables and transformations (Sec. 2.3).

## Evaluation protocol (if any)
Controlled study, 2 (tool: Voyager vs PoleStar, a Tableau-like manual tool built on Vega-lite) x 2 (dataset) mixed design, counterbalanced; 16 participants (14 graduate, 2 undergraduate), 30 min per session, think-aloud, ~2 h total, $15 gift certificate; linear mixed-effects models with likelihood-ratio tests (Sec. 6.1).

## Key reported results (exact numbers with location)
- Unique variable sets shown: chi2(1,N=32)=38.056, p<0.001; interacted: chi2=19.968, p<0.001; Voyager +69.0 shown over baseline 30.6, +13.4 interacted over baseline 27.2 (Sec. 6.2.1).
- Bookmark count: no tool effect, chi2=0.060, p=0.807; baseline 9.7 per session (Sec. 6.2.2).
- 124 of 179 Voyager bookmarks (69%) include a recommender-added variable; majority for 12/16 subjects (Sec. 6.2.3).
- Preference: 15/16 (94%) Voyager for exploration, 15/16 (94%) PoleStar for question answering (Sec. 6.2.4).
- 15/16 rated recommendations Helpful/Very Helpful; 8/16 (50%) agreed they "need improvement" (Sec. 6.2.4).
- No evaluation of ranking accuracy against ground truth was found.

## Stated limitations
- Weights manually tuned; automatic determination is future work (Sec. 5.2).
- Only single-step variable additions, deterministic heuristics; scalability to many variables deferred (Sec. 5.2, 7).
- Voyager is cumbersome for specific questions; hybrid with manual tools suggested (Sec. 6.2.5, 7).
- Large plots do not fit gallery cells (open question) (Sec. 7).

## Code/data availability (as stated)
Voyager, Compass, PoleStar and Vega-lite released as open source at http://vega.github.io (Sec. 7).

## Relevance to a system that recommends charts from a SQL query + its result set (Reviewer note)
Its encoding enumeration and effectiveness ranking (type-by-channel tables, cardinality penalties) map directly onto a result set whose columns have types and cardinalities. Differences: it explores variable subsets of a base table; a SQL system fixes the variables and aggregation via the query. Ranking is hand-tuned heuristics, a possible rule baseline.

## Comparability issues
- User study measures exploration coverage, not recommendation correctness; no accuracy/NDCG numbers to compare.
- Small sample (16, students), two datasets, tool compared is the authors' own PoleStar.
- Early Vega-lite version (static charts only, no interaction).
