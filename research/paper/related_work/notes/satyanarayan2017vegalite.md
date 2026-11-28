# Satyanarayan et al. 2017 - Vega-Lite: A Grammar of Interactive Graphics (IEEE TVCG 23(1), DOI 10.1109/TVCG.2016.2599030)

## Source
https://idl.cs.washington.edu/files/2017-VegaLite-InfoVis.pdf (author-hosted PDF). Full text read.

## Problem formulation
Provide a high-level declarative grammar for interactive graphics: low-level toolkits (D3, Vega) are verbose; high-level grammars (ggplot2, Tableau) have limited interaction support (Sec. 1). Contribution: a view algebra (layer, concat, facet, repeat) plus a grammar of interaction built on "selections".

## Input and output
Input: JSON specification (unit or composite). Output: compiled low-level Reactive Vega JSON specification (Sec. 5).

## Data (if any; source, size, availability as stated)
No dataset study. Examples use weather data, stocks, flights (hour/delay/distance) (Figs 2, 9, 11).

## Method
- Unit spec = (data, transforms, mark-type, encodings) (Sec. 3.1); marks: bar, line, area, text, rule, point, tick; encoding = (channel, field, data-type, value, functions, scale, guide); data types nominal, ordinal, quantitative, temporal.
- Missing details filled by defaults, e.g. quantitative color gets a sequential palette (Sec. 3, 5).
- Selections define event processing, points of interest and a predicate; they parameterize encodings via conditionals, input data, scale extents (Sec. 4).
- Compiler phases: parse, build, merge, assemble; merge example 2N vs 2N^2 scales in a SPLOM (Sec. 5).
- Related work: Polaris/Tableau grammar; an early Vega-Lite "is used to automatically recommend static plots as part of the Voyager browser" (Sec. 7).

## Evaluation protocol (if any)
Example-based: expressivity checked by covering the Yi et al. interaction taxonomy (select, explore, connect, abstract/elaborate, reconfigure, filter, encode); authoring speed assessed by comparing specifications against canonical Reactive Vega examples (Sec. 6). No user study found.

## Key reported results (exact numbers with location)
- Common interaction methods "typically 1-2 lines of code" (Sec. 2.2).
- Reactive Vega techniques "tens of lines of JSON" (Sec. 2.2).
- Reactive Vega has "interactive performance at least twice as fast as the equivalent D3 program" (Sec. 2.2, citing [22]; not a Vega-Lite measurement).
- No timing or line-count table for Vega-Lite itself was found in the text.

## Stated limitations
- Compile-time components cannot be manipulated interactively (e.g. no selection choosing fields to bin/aggregate); no lasso (no arbitrary path marks); some encode-type techniques do not yet produce valid Vega (Sec. 7, Sec. 6).
- Model favors conciseness over expressivity; specialized techniques (e.g. relaxed selections) not expressible by default.
- View algebra cannot visually link marks across views (Sec. 7).
- Future: recommend interaction methods (Sec. 7).

## Code/data availability (as stated)
Open source, http://vega.github.io/vega-lite/ (Sec. 7).

## Relevance to a system that recommends charts from a SQL query + its result set (Reviewer note)
Useful as an output target: a recommender can emit a Vega-Lite JSON spec (mark + typed encodings) with defaults for scales and axes. The paper itself does no recommendation; it only notes Voyager uses an earlier version.

## Comparability issues
- A language/toolkit paper; no accuracy, user or benchmark results, so nothing to compare numerically with recommenders.
- Compared with recommenders only as an enumerable design space.
