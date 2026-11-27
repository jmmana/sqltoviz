# Deduplication and grouped splits (E01-08, #26)

`sqltoviz_data.splits`: `normalize_sql` (literals/numbers → `?`, case/whitespace collapsed), `dedup` (within-group near-duplicate removal), `grouped_stratified_split` (whole groups → one split, greedy class-balanced, seeded) and `audit_splits` (asserts: unique ids, full coverage, no group and no (group, template) spanning splits).

## Real-data findings (2026-11-27, `tools/split_report.py`)
- DB overlap: Spider train∩dev = 0; Spider dev∩BIRD dev = 0; **Spider train∩BIRD dev = {formula_1}**. Groups must therefore use the canonical DB name across corpora (namespacing per corpus would have allowed one schema family in two splits).
- Dedup (stand-in, within DB): 9568 queries → 5938 kept, 3630 dropped (38%); 34 templates appear in more than one DB (kept, reported).
- Grouped split (seed 20261127): train 4177 items/118 DBs, val 885/26, test 876/26; audit passes.
- The class stratum used in this report is a stand-in (column count/aggregate flag), **not chart labels**; real class balance is audited in notebook 01 once labels exist (#24/#27). Classes with fewer groups than splits cannot be stratified; the notebook must report per-class support per split and merge/flag rare classes instead of hiding them.

## Limits
Near-duplicate detection is lexical (normalized SQL), not semantic. Group split removes schema leakage but not cross-schema domain similarity (e.g. several movie databases).
Tests: `pytest tests/test_splits.py` → 6 passed.
