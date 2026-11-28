# yang2023draco2 (Yang, Gyarmati, Zeng, Moritz, arXiv 2308.14247)
Full text read (4 pages, short paper).

## Source
https://arxiv.org/pdf/2308.14247 (arXiv:2308.14247v1 [cs.HC], 28 Aug 2023). Paper discusses software version 2.0.0.

## Problem formulation
Draco 1 is hard to use: limited tooling and documentation, spec language tied to Vega-Lite, only single and faceted views (Abstract, Sect. 1). Draco 2 is presented as a successor platform, not a new recommendation algorithm.

## Input and output
Input: chart specification as nested dict or flat ASP facts (entity/attribute facts), complete or partial, plus optional data schema (e.g. from a pandas DataFrame via schema_from_dataframe) and primary task (Sects. 3.1, 4). Output: completed specifications ranked by cost (Draco.complete_spec), rendered by default through a Vega-Lite/Altair renderer (Sects. 3.3, 4).

## Data (source, size, license/availability as stated)
No new dataset. Comparison uses 100 visualization pairs from Kim and Heer [10]'s graphical perception dataset (Sect. 3.4). Demonstration uses the Seattle weather dataset (Sect. 4, footnote 6). Licence of the software is not stated in the paper.

## Method
Knowledge base of hard and soft constraints over facts, as in Draco 1; default knowledge base "consists of constraints adopted from CompassQL rules" (Sect. 3.2). New: entity/attribute specification format independent of Vega-Lite; scales as explicit entities; multi-view and layered charts; encoding data type inferred from primitive field type plus scale type; Python-only implementation, REST API, WebAssembly package; debugger and plotter modules for violation vectors (Sects. 1, 3). Draco-Learn learns weights "the learning algorithm is the same as in Draco 1" (Sect. 3.2).

## Evaluation protocol (splits, metrics, baselines)
No benchmark evaluation. (1) Agreement of Draco 1 vs Draco 2 rankings on 100 pairs using default knowledge bases and weights (Sect. 3.4). (2) Qualitative walkthrough on Seattle weather (Sect. 4).

## Key reported results (exact numbers with location)
- "the two systems agreed on the ranking 86% of the time" on 100 pairs; in divergent cases "Draco 2 preferred the visualization which was also deemed better by the participants of Kim and Heer's study" (Sect. 3.4).
- 147 soft constraints in the knowledge base; 18 of 147 affected the top recommendations in the first exploration, 40 of 147 in the synthesized-query exploration (Sect. 4).
- "100% unit test coverage" (Sect. 1).

## Stated limitations
- Draco 1 limits (motivation): single/faceted views only, Vega-Lite-bound, little documentation, low test coverage (Sect. 1).
- Identical-looking charts can receive different costs because entities such as "task" affect cost but not the rendered spec (Sect. 4).
- Recommendations from the demo include non-expressive designs (e.g. faceted heatmaps for rect+color) not penalized by existing soft constraints (Sect. 4).
- "even slight weight changes to the knowledge base can lead to very different results" (Sect. 3.4).
- Future work only: LLM generates a partial spec and Draco completes it; fine-grained task taxonomies; interactive charts (Sect. 5).

## Code/data availability (as stated)
Open source at github.com/cmudig/draco2 (Sect. 1); documentation at dig.cmu.edu/draco2; npm package draco-pyodide (Sect. 3.3). Licence not stated in the paper.

## Relevance to a system that recommends charts from a SQL query + its result set (Reviewer note)
- Reviewer note: Draco 2 can build a schema from a DataFrame, so a query result set can be fed directly; it still has no SQL input.
- Reviewer note: its suggested LLM + Draco split (Sect. 5, proposal only, not evaluated) is architecturally close to an LLM that proposes a spec and a rule-based checker that validates or completes it.
- Reviewer note: constraint violations (e.g. size_without_point_text) could act as a validity filter for generated chart specs.

## Comparability issues
- Reviewer note: the paper gives no accuracy of recommended charts against any labelled corpus; the 86% is self-agreement between two versions of the same system.
- Reviewer note: defaults are CompassQL-derived, so any Draco 2 baseline reflects 2016-era heuristics unless weights are retrained.
- Reviewer note: 4-page short paper; details (e.g. runtime) are in the documentation, which was not read.
