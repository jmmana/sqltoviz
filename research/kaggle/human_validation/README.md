# Human validation (100 reserved cases)

- `human_validation_100_cases.xlsx` - **the file for evaluators**: instructions (EN + ES summary), chart guide, 100 shuffled cases (SQL, result size, columns and first 20 rows) with drop-downs for preferred chart, valid alternatives, confidence and observations. It contains **no** LLM labels, model predictions, synthetic labels, stratum or provenance (checked by tests and by a scan of the real workbook; the only match for "llm" is the surname "Willms" in the data).
- `human_validation_key.csv` - case id -> internal item id. **Do not send to evaluators.**
- Return flow: `tools/ingest_human_validation.py KEY_CSV evaluator1=filled1.xlsx [evaluator2=filled2.xlsx]` validates answers (rows with no choice or "other" are reported as problems), writes `annotations/human_labels.jsonl` (label_source = human, kept apart from LLM and synthetic labels) and `reports/human_validation_report.json` (human-vs-LLM and human-vs-human kappa/agreement).
- Data are Spider-train queries (CC BY-SA 4.0, see ATTRIBUTION in ACQUISITION.md); suggest at least two independent evaluators so human-human agreement can be reported.
