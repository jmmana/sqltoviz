# TPC-H / TPC-DS samples (E01-04, #22)

`python -m sqltoviz_data.tpc {tpch|tpcds} --sf 0.1 --out data/tpc-eula` generates a DuckDB database per benchmark (separate files: table names collide) plus a manifest with DuckDB version, scale factor, row counts and an order-independent per-table content hash. Only the script is distributed; generated data stays local in the `tpc-eula` namespace (EULA v2.2.0). Timings from these data are **not TPC Benchmark Results**.

## Evidence (2026-11-27, DuckDB 2.0.1)
- TPC-H SF=0.1: customer 15 000, orders 150 000, supplier 1 000, part 20 000, partsupp 80 000, nation 25, region 5, lineitem 600 572 — customer/orders/supplier/part/partsupp match the specification's SF scaling (150k/1.5M/10k/200k/800k × SF); tests assert the SF=0.01 values.
- TPC-DS SF=0.1: 24 tables, 1 176 170 rows total (store_sales 288 464).
- Determinism: TPC-H regeneration yields identical per-table hashes (tested). **Not tested:** TPC-DS hash determinism and TPC-DS row counts against the official specification; do not claim spec conformance for TPC-DS.
- Seeds: DuckDB's generators take no seed; reproducibility relies on pinned DuckDB version + SF + the manifest hashes.

Tests: `pytest tests/test_tpc.py` → 5 passed.
