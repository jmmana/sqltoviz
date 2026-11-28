# Dibia, LIDA (arXiv 2303.02927)
Full text read (PDF via arxiv.org, pdftotext). Appendices are referenced in the text; only what the extraction contained is reported. Figure 6 bar labels were read from text extraction and the bar-to-grammar mapping could not be verified.

## Source
https://arxiv.org/pdf/2303.02927, version v3 (cs.AI, 6 Jun 2023). Title: "LIDA: A Tool for Automatic Generation of Grammar-Agnostic Visualizations and Infographics using Large Language Models" (tool/demo-style paper). Footnote 1: work "primarily utilizes the OpenAI gpt-3.5-turbo-x line of models".

## Problem formulation
- Visualization generation posed as a multi-stage generation problem: understand data semantics, enumerate visualization goals, generate specifications (Abstract; Introduction). Two modes: fully automated (system proposes goals) and semi-automated (user gives goal) (Introduction).

## Input and output
- Input: a dataset (tabular), optionally a natural-language goal or refinement instruction (multilingual claimed via the underlying LLM).
- Output: visualization code (e.g. Python libraries Matplotlib, Seaborn, Plotly, Altair, Bokeh, GGPlot; also Vega-Lite named as a grammar), executed to produce a chart; optional infographic from an image generation model. A goal is a JSON object with "question", "visualization", "rationale" (Fig. 4).

## Data (source, size, license/availability as stated)
- No training data: prompted LLMs, no training. Evaluation benchmark: 57 datasets from the vega-datasets repository (Sec. 4.2). No license statement found in the text apart from calling LIDA an "Open Source library" (Introduction).

## Method
- Four modules (Sec. 3): SUMMARIZER (Stage 1: pandas atomic types, min/max/number of unique values, n random non-null samples per column; Stage 2: optional LLM/user enrichment with dataset and field descriptions and semantic types; Fig. 3); GOAL EXPLORER (LLM generates question, visualization, rationale); VIS GENERATOR (code scaffold constructor, code generator using LLM in fill-in-the-middle mode generating n candidates, code executor with filtering: discard non-compiling, self-consistency, or correctness probabilities); INFOGRAPHER (text-conditioned image-to-image diffusion via Peacasso).
- VISOPS: NL refinement, explanations/accessibility descriptions, self-evaluation and repair, recommendation of further visualizations (Sec. 3.2.2).

## Evaluation protocol (splits, metrics, baselines)
- Called "initial evaluation" (Sec. 4). Metrics: Visualization Error Rate VER = percent of generated visualizations with code compilation errors (Sec. 4.1.1); Self-Evaluated Visualization Quality SEVQ = GPT-4 scores code 1-10 on 6 dimensions (code accuracy, data transformation, goal compliance, visualization type, data encoding, aesthetics) (Sec. 4.1.2).
- Benchmark: 57 vega-datasets datasets, 5 goals per dataset, 1 visualization per goal, multiple grammars; temperature = 0, n = 1 (Sec. 4.2). Single try per step (footnote 6).
- No baselines and no human evaluation reported. Ablation over summary type: no_enrich, enrich, schema (field names only), no_summary (Sec. 4.3, Fig. 6).

## Key reported results (exact numbers with location)
- Overall VER = 3.5% (Sec. 4.3, text).
- Fig. 6 (title "Visualization Error Rate | GPT-3.5, n=2280"): values printed in the figure: 5.61%, 3.51%, 7.72%, 3.51%, 7.02%, 9.47%, 95.79%, 99.30%. Reviewer note: the text extraction does not show which bar each value belongs to; the text states a summary lowers VER versus schema-only, enrichment has less effect, and Seaborn has lower VER. The 95.79%/99.30% values presumably correspond to the no_summary condition but this is not stated in the text.
- No SEVQ numeric result is reported in the text read; SEVQ is illustrated qualitatively (Fig. 10, pie chart critiqued and bar chart suggested).

## Stated limitations
- Low-resource grammars (GUI tools such as Tableau, PowerBI) and complex tasks needing complex data transformations may perform poorly (Limitations section).
- LLM cost and latency, and the code execution step requires a sandbox (Limitations section, footnote 4).
- Interpretability of LLM behavior; need for more comprehensive benchmarks on more datasets and grammars (Limitations section).

## Code/data availability (as stated)
- Code and demo at https://microsoft.github.io/lida/ (Abstract); described as an Open Source library with a python API, web API and web interface (Introduction). A gallery of generated evaluation visualizations is on the project page (Sec. 4.2).

## Relevance to a system that recommends charts from a SQL query + its result set (Reviewer note)
- Reviewer note: LIDA operates on a dataset summary (a result set could be passed as a dataframe); it does not take a SQL query as input. The SUMMARIZER's profile (types, uniques, samples) is analogous to features computed from a result set.
- Reviewer note: it generates code and can pick or transform columns via LLM, so correctness depends on a proprietary LLM and sandboxed execution; outputs are not ranked against labeled ground truth.

## Comparability issues
- Reviewer note: VER measures only whether code compiles/executes, not whether the chart is appropriate; SEVQ is LLM-judged by GPT-4 without reported human validation in the text. Neither is comparable to accuracy, recall@k or human-consensus scores of VizML/Table2Charts.
- Reviewer note: no baseline systems are run in this paper; the claim "effective compared to state of the art systems" (Conclusion) is supported only by a gallery, not by a reported comparison.
- Reviewer note: results use gpt-3.5-turbo variants at temperature 0 and may not reproduce with other model versions.
