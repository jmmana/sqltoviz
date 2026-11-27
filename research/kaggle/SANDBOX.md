# Sandboxed query execution (E01-05, #23)

`sqltoviz_data.sandbox` (SQLite) and `sqltoviz_data.sandbox_duckdb` (DuckDB, for TPC samples) execute corpus SQL under: read-only/immutable open, authorizer allow-list (SQLite) or `enable_external_access=false` + locked config (DuckDB), single SELECT/WITH/VALUES statement, wall-clock timeout, VM-step budget, row cap with explicit `truncated` flag, and optional subprocess isolation with CPU/memory rlimits (`execute_isolated`).

Threat model: untrusted *SQL text*. A hostile database file is out of scope.

## Evidence (2026-11-27, `tools/corpus_exec_check.py`, 10 s timeout)
| Corpus (gold queries) | n | ok | timeout | other |
|---|---|---|---|---|
| Spider dev | 1034 | 1034 | 0 | 0 |
| BIRD dev (20240627) | 1534 | 1527 | 7 | 0 |

The 7 BIRD timeouts are queries exceeding 10 s on this machine; they are excluded from labeled data rather than retried with larger budgets. Running the check surfaced invalid UTF-8 in Spider `wta_1` (fixed: lossy decode, regression-tested).

Tests: `pytest research/kaggle/tests` → 34 passed (mutations/ATTACH/PRAGMA/load_extension/stacked statements/external file read rejected with file hash unchanged; infinite recursion and cross-join time out; row cap; invalid UTF-8).
