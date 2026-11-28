# moritz2018draco (Moritz et al., IEEE TVCG 2019)
Full text read (11 pages). Page numbers/section numbers below refer to this preprint.

## Source
https://idl.cs.washington.edu/files/2019-Draco-InfoVis.pdf (IDL preprint; header still reads "Manuscript received xx xxx. 201x", DOI placeholder). A second copy (par.nsf.gov/servlets/purl/10074159) was downloaded but only 4 of 11 pages were text-extractable, so it was not used.

## Problem formulation
Gap between visualization design guidelines and their use in tools (Abstract). Proposes representing design knowledge as hard and soft constraints, plus learning soft-constraint weights from experimental data (Abstract, Sect. 1). Recommendation = finding the lowest-cost answer set (Sect. 4.3). "Optimal" means optimal under the formal preferences, not the definitively best design (Sect. 4).

## Input and output
Input: a dataset/schema, a partial Vega-Lite-like specification (blank attributes), optionally a user task (Sect. 4.3.1, Fig. 5). Output: complete specification(s) converted to Vega-Lite (Sect. 4.3.2). Scope: single views and faceted views (row/column); marks bar, line, area, point (tick/text also mentioned) (Sects. 2.3, 4.2.1).

## Data (source, size, license/availability as stated)
No dataset is released as a benchmark. Training pairs are harvested from two published perception studies: Kim and Heer [30]: 12 scatterplot encodings, "185,000 responses from 1,920 participants"; Saket et al. [51]: "180 participants" (Sect. 6.3). Harvest yields "about 1,100 pairs from Kim et al. and 10 pairs from Saket et al." (Sect. 6.3.1; Fisher's test, p < 0.01). Example query uses cars.csv (num_rows(407)) (Sect. 4.3.2).

## Method
Visualization = logical facts (mark/1, encoding/1, channel/2, field/2, aggregate/2, bin/2, ...); data schema facts (num_rows, fieldtype, cardinality, entropy, extent); task/1 (value vs summary) (Sect. 4.1). Aggregate rules + hard integrity constraints (well-formedness, expressiveness) define the space; soft constraints with weights define Cost(v) = sum of weight x violation count (Sect. 4.2). Solved with Clingo (ASP). Weights learned with RankSVM on ranked pairs of full specifications, lambda = 0.1 (Sect. 5). Preference model interpreted as a Markov logic network (Appendix).

## Evaluation protocol (splits, metrics, baselines)
(a) Draco-APT and Draco-CQL re-implementations; baseline CompassQL on its test suite of 17 partial specifications; runtime benchmark vs CompassQL on CentOS, Xeon E5-2690 v3 2.60 GHz (Sect. 6.2). (b) Draco-Learn: ranked-pair accuracy; split 55% train / 15% validation / 30% test; baseline Draco-CQL hand-tuned weights (Sect. 6.3.2). No user study of recommendations.

## Key reported results (exact numbers with location)
- Draco-CQL "synthesizes identical optimal specifications as CompassQL for all 17 partial specifications" (Sect. 6.2).
- Draco-CQL = "70 hard and 110 soft constraints"; CompassQL = "4,324 lines of imperative code, with 1,134 ... hard constraints and 786 ... scoring logic" (Sect. 6.2).
- 25 fields, 5 encodings: Draco "less than half a second"; CompassQL "runs out of heap memory after a few minutes" (Sect. 6.2, Fig. 7; heap set to 4 GB).
- Learned model: 93% test accuracy on ranked pairs vs 65% for hand-tuned Draco-CQL (Sect. 6.3.2); 96% validation accuracy at p-threshold 0.1; test accuracy falls behind validation below 250 training pairs.
- In all conditions (48 for Kim et al., 8 for Saket et al.) Draco-Learn returns a top-performing encoding for the harvested data (Sect. 6.3.2).

## Stated limitations
- Model supports marks, encodings, binning and aggregation only; filtering, sorting and interaction primitives are planned (Sect. 7.2).
- Single/faceted views only; layered views and dashboards are future work (Sect. 7.2).
- Draco-Learn modeled "a restricted subspace of visualizations that mirrors the limits of the available experimental data" (Sect. 7.2).
- Learned weights inherit "the same generalizability and validity issues that all empirical studies have" (Sect. 6.3).
- Effects of low-level features such as over-plotting are not captured (Sect. 7.2).
- Tooling for developers is described as future work (Sect. 7.2).

## Code/data availability (as stated)
"We make Draco available as open source software ... at https://uwdata.github.io/draco/" (Sect. 1). Licence not stated in the paper. Supplemental material lists full constraints (Sect. 4.2).

## Relevance to a system that recommends charts from a SQL query + its result set (Reviewer note)
- Reviewer note: Draco takes a table schema with statistics (cardinality, entropy, extent) and a partial spec, which maps naturally to a result set's columns; it has no SQL input and no notion of query semantics (GROUP BY, ORDER BY, LIMIT).
- Reviewer note: it is a knowledge-based ranker, a plausible non-neural baseline or a rule layer after a learned model.
- Reviewer note: the paper reports no end-to-end chart-selection accuracy against human-labelled charts; only pair ranking on perception data.

## Comparability issues
- Reviewer note: the 93%/65% figures measure pairwise ranking on perception-study pairs (~1,100 pairs), not chart-type prediction; not comparable with nvBench/ncNet accuracy.
- Reviewer note: effectiveness here means task accuracy/time in perception studies; no judgment of appropriateness for a given query.
- Reviewer note: preprint, not the camera-ready TVCG text; check numbers against the published version before citing.
