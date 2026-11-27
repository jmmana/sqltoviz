"""Sandboxed read-only SQL execution on DuckDB (used for TPC-H/TPC-DS samples).

Opens the database read-only, disables external file/network access, locks the
configuration, allows a single SELECT/WITH/VALUES statement, enforces a
wall-clock timeout through ``interrupt()`` and a row cap.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

import duckdb

from .sandbox import ERROR, OK, REJECTED, TIMEOUT, QueryResult, _single_statement


def execute(db_path: str | Path, sql: str, *, timeout_s: float = 10.0, max_rows: int = 10_000,
            memory_limit: str = "1GB", threads: int = 2) -> QueryResult:
    start = time.monotonic()
    if not _single_statement(sql):
        return QueryResult(REJECTED, message="exactly one SELECT/WITH/VALUES statement required")
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except duckdb.Error as e:
        return QueryResult(ERROR, message=f"open failed: {e}")
    timed_out = threading.Event()
    try:
        con.execute("SET enable_external_access=false")
        con.execute(f"SET memory_limit='{memory_limit}'")
        con.execute(f"SET threads={int(threads)}")
        con.execute("SET lock_configuration=true")

        def _kill():
            timed_out.set()
            con.interrupt()

        timer = threading.Timer(timeout_s, _kill)
        timer.start()
        try:
            cur = con.execute(sql)
            cols = [d[0] for d in (cur.description or [])]
            rows = cur.fetchmany(max_rows + 1)
        except duckdb.Error as e:
            if timed_out.is_set():
                return QueryResult(TIMEOUT, message="time budget exceeded", elapsed_s=time.monotonic() - start)
            msg = str(e)
            st = REJECTED if ("read-only" in msg.lower() or "permission" in msg.lower() or "disabled" in msg.lower()) else ERROR
            return QueryResult(st, message=msg, elapsed_s=time.monotonic() - start)
        finally:
            timer.cancel()
        trunc = len(rows) > max_rows
        return QueryResult(OK, cols, [list(r) for r in rows[:max_rows]], trunc, time.monotonic() - start)
    finally:
        con.close()
