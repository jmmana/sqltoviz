# Chart annotation task (blind)

You see data-analysis SQL queries (from a public text-to-SQL benchmark) with the **result columns and up to 20 result rows**
(`rows_preview`; `result_truncated=true` means the real result has more rows). For each item decide which visualization
would be appropriate to show this result to a person.

Choose from exactly these 10 classes:
- `kpi`: one scalar metric (or a metric with one comparison); typically a single row.
- `bar`: compare a measure across a moderate number of categories (vertical).
- `horizontal_bar`: ranking or comparison where category labels are long or categories are many.
- `stacked_bar`: a measure split by two categorical dimensions where the parts are additive and groups disjoint.
- `line`: a measure over an ordered temporal/sequential dimension.
- `area`: like line, but magnitude from a zero baseline is meaningful (volumes, cumulative amounts).
- `donut`: parts of a whole: few mutually exclusive categories of a non-negative additive measure.
- `scatter`: relationship between two (or three) quantitative measures, one point per observation.
- `heatmap`: two categorical dimensions and one measure (grid of cells).
- `table`: no chart is justified (detail rows, text, identifiers, many mixed columns, ambiguous or unsafe to aggregate).

Rules: judge from the SQL and the result only. Several charts can be valid: give a `primary` (your preferred one) and an
`acceptable` list (all classes you consider valid, including the primary). If a chart would be misleading (e.g. stacking
non-additive values, pie of ratios) prefer `table` or a safe alternative. `confidence`: 1 low, 2 medium, 3 high.

Output: JSON Lines, one object per input item, in the same order, exactly these keys:
{"item_id": str, "primary": class, "acceptable": [class,...], "confidence": 1|2|3, "rationale": "<=20 words"}
Annotate ALL items. Do not invent items. Work only from this directory's `pack.jsonl` and this file. Do not look for or read any
other files, labels, model outputs or other annotators' work; do not run code that infers labels automatically - judge each item yourself.
