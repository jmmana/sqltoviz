"""Generate TPC-H / TPC-DS samples locally with DuckDB's tpch/tpcds extensions.

Only scripts are distributed; generated data stays local (TPC EULA v2.2.0, see
DATASET_LICENSE_AUDIT.md). Each benchmark goes to its own database file because
table names collide (e.g. ``customer``). A manifest records DuckDB version,
scale factor and a per-table content hash so regeneration can be verified.
Any timing derived from these data is NOT a TPC Benchmark Result.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

BENCHMARKS = {"tpch": "dbgen", "tpcds": "dsdgen"}
NOTICE = "Generated with DuckDB extension; not a TPC Benchmark Result and not comparable to one."


def table_hash(con, table: str) -> str:
    """Order-independent content hash (sum of per-row md5 as hugeint)."""
    cols = [r[0] for r in con.execute(
        "select column_name from information_schema.columns where table_name=? order by ordinal_position",
        [table]).fetchall()]
    row_expr = "concat_ws('|', " + ", ".join(f"coalesce(cast(\"{c}\" as varchar),'<NULL>')" for c in cols) + ")"
    # hash(...) is stable within a DuckDB version; md5_number_lower/upper are stable across versions.
    q = (f"select cast(sum(cast(md5_number_lower({row_expr}) as hugeint)) as varchar) || ':' || "
         f"cast(sum(cast(md5_number_upper({row_expr}) as hugeint)) as varchar) from \"{table}\"")
    return con.execute(q).fetchone()[0]


def generate(benchmark: str, out_dir: Path, sf: float = 0.01) -> dict:
    if benchmark not in BENCHMARKS:
        raise ValueError(f"benchmark must be one of {sorted(BENCHMARKS)}")
    if sf <= 0:
        raise ValueError("scale factor must be positive")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    db_path = out_dir / f"{benchmark}_sf{sf}.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    try:
        con.execute(f"INSTALL {benchmark}")
        con.execute(f"LOAD {benchmark}")
        con.execute(f"CALL {BENCHMARKS[benchmark]}(sf={sf})")
        tables = [r[0] for r in con.execute(
            "select table_name from information_schema.tables where table_schema='main' order by 1").fetchall()]
        info = {t: {"rows": con.execute(f'select count(*) from "{t}"').fetchone()[0], "hash": table_hash(con, t)}
                for t in tables}
    finally:
        con.close()
    manifest = {"benchmark": benchmark, "scale_factor": sf, "duckdb_version": duckdb.__version__,
                "namespace": "tpc-eula", "notice": NOTICE, "database": db_path.name, "tables": info}
    (out_dir / f"{benchmark}_sf{sf}.manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("benchmark", choices=sorted(BENCHMARKS))
    ap.add_argument("--sf", type=float, default=0.01)
    ap.add_argument("--out", default="data/tpc-eula")
    ns = ap.parse_args(argv)
    m = generate(ns.benchmark, Path(ns.out), ns.sf)
    print(json.dumps({t: v["rows"] for t, v in m["tables"].items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
