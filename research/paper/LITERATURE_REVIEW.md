# Related work (E08-01, #89)

**Provenance and limits.** All 19 references were verified by `tools/verify_references.py` against arXiv/Crossref (exact title + first-author match; `related_work/verification_report.json`, retrieved 2026-11-27; BibTeX in `references.bib` is generated only from those responses). The descriptions below rest on the verified titles and, where the API returns one, the abstracts. **Full texts have not yet been read**; this is a first-pass review, so no novelty claim is made (as required by `spec/chart-taxonomy-v1.md`) and detailed comparisons with numbers from those papers are deliberately absent.

## Landscape (grouped by problem formulation)
| Line of work | Representative verified references | Input -> output (as stated in titles/abstracts) |
|---|---|---|
| Rule/constraint-based chart design | Show Me (Mackinlay et al., 2007); Voyager (Wongsuphasawat et al., 2016); Draco (Moritz et al., 2019) and Draco 2 (Yang et al., 2023); Vega-Lite (Satyanarayan et al., 2017) | Data attributes -> visual encodings/charts via encoded design knowledge (Draco: constraints; Draco 2: extensible platform); Vega-Lite is a grammar, used here as an expert-authored source of channel assignments |
| Learned recommendation from (data, chart) corpora | VizML (Hu et al., 2019); DeepEye (Luo et al., 2018); Table2Charts (Zhou et al., 2020); Data2Vis (Dibia and Demiralp, 2019) | Dataset/table -> visualization design choices or chart specs. VizML (abstract): features from datasets, five design choices (e.g. chart type, X/Y encoding) learned from a large corpus; Table2Charts (abstract): 165k tables / 266k charts, table-to-sequence generation; Data2Vis (abstract): sequence-to-sequence translation of data specs to visualization specs |
| Natural language to visualization | nvBench (Luo et al., 2021), ncNet (Luo et al., 2022), LIDA (Dibia, 2023) | NL (+ data) -> visualization; nvBench is a benchmark synthesized from NL2SQL benchmarks; LIDA (abstract): LLM pipeline with summarizer, goal exploration and generation modules |
| Text-to-SQL substrates | Spider (Yu et al., 2018), BIRD (Li et al., 2023) | NL -> SQL; abstracts: Spider 10,181 questions / 5,693 queries / 200 databases; BIRD 12,751 pairs / 95 databases / 33.4 GB. Used here only as sources of SQL + databases |
| Methods and measurement | Cohen (1960) kappa; Breiman (2001) random forests; scikit-learn (Pedregosa et al.); Leys et al. (2013) MAD; Zhu et al. (2020) survey | agreement statistics, the classifier family, library, robust outlier statistic, survey of visualization recommendation |

## Positioning of this work (hypotheses about differences, not claims)
1. **Input contract.** SQL text (lexical features only) plus the executed result set; no natural-language request and no corpus of existing charts at inference time.
2. **Hierarchical, auditable output.** A classifier ranks 10 base candidates; a deterministic specializer and hard semantic constraints produce 21 outputs, with reason codes and fail-closed fallback to `table` (taxonomy v1). Whether this reduces unsafe recommendations is RQ2 and is tested, not assumed.
3. **Portability.** A frozen, versioned feature contract with cross-runtime parity fixtures and an ONNX model (RQ5/RQ6) so Python, TypeScript and .NET SDKs compute identical features.
4. **Evaluation hygiene.** Labels of different provenance (synthetic / LLM / human) are kept separate; splits are grouped by database; label-leakage is measured (SYNTHETIC_DATA.md).

## Gaps to close before any novelty claim
Read the full texts of VizML, DeepEye, Table2Charts, Draco/Draco 2, nvBench/ncNet and LIDA; check whether public code/data allow a fair baseline comparison (VizML data are currently inaccessible and unlicensed - DATASET_LICENSE_AUDIT.md); search for SQL-input chart recommenders and for work on semantic-safety constraints (additivity, hierarchy) in recommendation; extend beyond 19 references.
