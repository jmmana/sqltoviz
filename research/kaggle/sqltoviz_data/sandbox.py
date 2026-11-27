"""Sandboxed, read-only SQL execution on SQLite databases.

Defence in depth:
1. database opened read-only + immutable (URI) and ``PRAGMA query_only``;
2. SQLite authorizer allow-lists read operations only (no ATTACH, PRAGMA,
   DDL/DML, transactions, extension loading);
3. exactly one statement;
4. wall-clock timeout and VM-step budget via the progress handler;
5. row cap (results are truncated and flagged, never silently dropped);
6. optional subprocess isolation with CPU/memory rlimits (``execute_isolated``).

This module executes untrusted *SQL text* from benchmark corpora; it does not
make arbitrary databases trustworthy (a hostile .sqlite file is out of scope).
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

OK, REJECTED, TIMEOUT, ERROR = "ok", "rejected", "timeout", "error"

_ALLOWED_ACTIONS = {
    sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
    sqlite3.SQLITE_RECURSIVE,
}


@dataclass
class QueryResult:
    status: str
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    truncated: bool = False
    elapsed_s: float = 0.0
    message: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)


def _authorizer(action, arg1, arg2, dbname, source):
    if action in _ALLOWED_ACTIONS:
        # block access to internal schema tables writes handled by action type;
        # reading sqlite_master is allowed (schema introspection is harmless).
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def _single_statement(sql: str) -> bool:
    s = sql.strip()
    if not s:
        return False
    # complete_statement is true if the text ends with ';' outside literals;
    # multiple statements are detected by trying to prepend/trim.
    body = s[:-1] if s.endswith(";") else s
    # sqlite3 module itself raises ProgrammingError for >1 statement in execute();
    # this pre-check just rejects obvious empties/stacked statements early.
    stripped = _strip_literals(body)
    if ";" in stripped:
        return False
    parts = stripped.split()
    return bool(parts) and parts[0].upper() in ("SELECT", "WITH", "VALUES", "(")


def _strip_literals(sql: str) -> str:
    out, i, n = [], 0, len(sql)
    while i < n:
        c = sql[i]
        if c in ("'", '"', "`"):
            q = c
            i += 1
            while i < n:
                if sql[i] == q:
                    if i + 1 < n and sql[i + 1] == q:
                        i += 2
                        continue
                    break
                i += 1
        elif c == "[":
            while i < n and sql[i] != "]":
                i += 1
        elif sql.startswith("--", i):
            while i < n and sql[i] != "\n":
                i += 1
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            i = n if j < 0 else j + 1
        else:
            out.append(c)
        i += 1
    return "".join(out)


def execute(db_path: str | Path, sql: str, *, timeout_s: float = 5.0,
            max_rows: int = 10_000, max_vm_steps: int = 50_000_000) -> QueryResult:
    start = time.monotonic()
    if not _single_statement(sql):
        return QueryResult(REJECTED, message="exactly one statement required",
                           elapsed_s=time.monotonic() - start)
    uri = f"file:{Path(db_path).resolve()}?mode=ro&immutable=1"
    try:
        con = sqlite3.connect(uri, uri=True, timeout=0)
    except sqlite3.Error as e:
        return QueryResult(ERROR, message=f"open failed: {e}")
    try:
        con.enable_load_extension(False) if hasattr(con, "enable_load_extension") else None
        con.text_factory = lambda b: b.decode("utf-8", "replace")  # corpora contain invalid UTF-8
        con.execute("PRAGMA query_only=ON")
        con.set_authorizer(_authorizer)
        deadline = start + timeout_s
        steps = {"n": 0}

        def progress():
            steps["n"] += 1000
            if time.monotonic() > deadline or steps["n"] > max_vm_steps:
                return 1  # abort
            return 0

        con.set_progress_handler(progress, 1000)
        try:
            cur = con.execute(sql)
            cols = [d[0] for d in (cur.description or [])]
            rows = cur.fetchmany(max_rows + 1)
        except sqlite3.DatabaseError as e:
            msg = str(e)
            if "interrupted" in msg:
                return QueryResult(TIMEOUT, message="time/step budget exceeded",
                                   elapsed_s=time.monotonic() - start)
            if "not authorized" in msg or "readonly" in msg:
                return QueryResult(REJECTED, message=msg, elapsed_s=time.monotonic() - start)
            return QueryResult(ERROR, message=msg, elapsed_s=time.monotonic() - start)
        except sqlite3.Warning as e:  # "You can only execute one statement at a time"
            return QueryResult(REJECTED, message=str(e), elapsed_s=time.monotonic() - start)
        trunc = len(rows) > max_rows
        rows = [list(r) for r in rows[:max_rows]]
        return QueryResult(OK, cols, rows, trunc, time.monotonic() - start)
    finally:
        con.close()


_CHILD = r"""
import sys, json, resource
cpu, mem = int(sys.argv[1]), int(sys.argv[2])
resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
try:
    resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
except (ValueError, OSError):
    pass
from sqltoviz_data.sandbox import execute
a = json.loads(sys.stdin.read())
sys.stdout.write(execute(**a).to_json())
"""


def execute_isolated(db_path: str | Path, sql: str, *, timeout_s: float = 5.0,
                     max_rows: int = 10_000, mem_bytes: int = 2 << 30) -> QueryResult:
    """Run :func:`execute` in a child process with CPU/memory limits and a hard kill."""
    payload = json.dumps({"db_path": str(db_path), "sql": sql, "timeout_s": timeout_s, "max_rows": max_rows})
    pkg_root = str(Path(__file__).resolve().parent.parent)
    start = time.monotonic()
    try:
        p = subprocess.run(
            [sys.executable, "-I", "-c", "import sys;sys.path.insert(0,%r);exec(%r)" % (pkg_root, _CHILD),
             str(int(timeout_s) + 2), str(mem_bytes)],
            input=payload, capture_output=True, text=True, timeout=timeout_s + 5)
    except subprocess.TimeoutExpired:
        return QueryResult(TIMEOUT, message="hard kill", elapsed_s=time.monotonic() - start)
    if p.returncode != 0:
        return QueryResult(ERROR, message=f"child exit {p.returncode}: {p.stderr[-200:]}",
                           elapsed_s=time.monotonic() - start)
    d = json.loads(p.stdout)
    return QueryResult(**d)
