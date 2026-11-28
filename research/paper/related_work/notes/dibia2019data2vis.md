# Dibia and Demiralp, Data2Vis (arXiv 1804.03126)
Full text read (PDF via arxiv.org, pdftotext). Section numbers are not preserved in the extraction; locations are given by section heading name or figure.

## Source
https://arxiv.org/pdf/1804.03126, version v3 (cs.HC, 2 Nov 2018). Authors listed: Dibia (Fitnescity Labs, e-mail at ibm.com) and Demiralp (MIT CSAIL). The text notes an earlier preprint was published and source code released (related work section).

## Problem formulation
- Visualization generation is cast as language translation: map a dataset specification to a Vega-Lite visualization specification (Abstract; Introduction).
- The model must select a subset of fields, learn field data types, and learn which transformations apply to which types (section on the model; view-level: aggregate, bin, calculate, filter, timeUnit; field-level: aggregate, bin, sort, timeUnit).

## Input and output
- Input (source sequence): JSON-encoded dataset (fields and values). In training, one single row per example; field names are replaced with "str"/"num" notation, then back-transformed in post-processing (Model section, Figure 3).
- Output (target sequence): a Vega-Lite specification, character-tokenized. Beam search (beam width 15 in Figure 6) is used to produce multiple candidate visualizations.

## Data (source, size, license/availability as stated)
- Training: 4300 Vega-Lite examples over 11 distinct datasets, from the corpus of [52] (compiled by the authors of that work with the CompassQL engine in Voyager 2, charts with 1-3 variables, filtered). Each example sampled 50 times with different data rows, giving 215,000 pairs (Model/training section).
- Six mark types (area, bar, circle, line, point, tick) and three transforms (aggregate, bin, timeUnit) (Figure 4).
- Test material: Rdatasets repository (stated as 1147 datasets, footnote 1), cleaned and converted to JSON, "not included in training".
- No license statement found.

## Method
- Seq2seq with attention: 2-layer bidirectional RNN encoder and 2-layer RNN decoder, each with 512 LSTM units; character vocabularies of 84 (source) and 45 (target) symbols; dropout 0.5; max source/target length 500; Adam, lr 0.0001; 20,000 steps, batch size 32. Implementation adapted from the neural machine translation framework of Britz et al. [13].
- LSTM chosen over GRU based on "valid json, valid Vega-Lite specification" results (no numbers given).

## Evaluation protocol (splits, metrics, baselines)
- Quantitative: log perplexity 0.032 reported for translation performance; no train/test split sizes are described in the text read.
- Qualitative: authors inspect outputs on random Rdataset datasets, plot attention weights (Figure 5), compare with Voyager 2 on one "race progression" dataset (Figure 9), and showed a web prototype to two visualization researchers (observational, no measured results).
- No accuracy metric, no quantitative baseline comparison, no user study with numbers.

## Key reported results (exact numbers with location)
- Log perplexity 0.032 (training section).
- "in all cases, the model generates a perfectly valid JSON file and valid Vega-Lite specification with some minor failure cases" (Examples section, qualitative claim, no count given).
- Limitations occur "in about 15-20% of tests" (Discussion, "Field Selection and Transformation").

## Stated limitations
- About 15-20% of tests show failures: phantom fields (fields not in the input; the axis is then uninterpretable), selection of fields with little information value, only simple univariate/bivariate plots, no complex transforms or multiple views (Discussion).
- Small and not diverse training data (4300 examples upsampled to 215,000 pairs); training from a single row means the model learns per-field properties but not distribution properties such as mean, range, categories (Discussion, "Training Data").
- Sequence model generates one output; extension to multiple plausible visualizations is future work (Discussion).

## Code/data availability (as stated)
- Source code stated as publicly available (reference [21]); web application at http://hci.stanford.edu/~cagatay/data2vis (Introduction contribution 3). Training corpus is from reference [52].

## Relevance to a system that recommends charts from a SQL query + its result set (Reviewer note)
- Reviewer note: input is a JSON dataset (row-level), conceptually similar to a result set serialized as JSON; no SQL query, question, or schema input.
- Reviewer note: output is a full Vega-Lite spec including field choice and aggregation, which overlaps with chart selection from a result set; its field selection step is unnecessary when the query already fixes the columns.
- Reviewer note: training specs come from a rule-based recommender (Voyager 2/CompassQL), so the model imitates rules rather than human choices.

## Comparability issues
- Reviewer note: no quantitative accuracy; only log perplexity (0.032) on an unspecified test split, and qualitative inspection. It cannot be compared numerically with classification accuracy or top-k results.
- Reviewer note: another paper (VizML, Sec. 8) evaluated Data2Vis on its own benchmark (CARS 75.61 two-class, 64.75 three-class per the VizML paper); those numbers are from VizML's protocol, not this paper.
- Reviewer note: training datasets (11) and mark types (6) are narrow; the Rdatasets test is not labeled with ground truth.
