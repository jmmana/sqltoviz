import hashlib
import sqlite3
from pathlib import Path

import pytest

from sqltoviz_data import sandbox as S


@pytest.fixture()
def db(tmp_path):
    p = tmp_path / "t.sqlite"
    c = sqlite3.connect(p)
    c.execute("create table t(a integer, b text)")
    c.executemany("insert into t values(?,?)", [(i, f"x{i}") for i in range(100)])
    c.commit(); c.close()
    return p


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_select_ok(db):
    r = S.execute(db, "SELECT a, b FROM t WHERE a < 3 ORDER BY a;")
    assert r.status == S.OK and r.columns == ["a", "b"] and r.rows == [[0, "x0"], [1, "x1"], [2, "x2"]]


@pytest.mark.parametrize("sql", [
    "INSERT INTO t VALUES (1,'z')", "UPDATE t SET a=1", "DELETE FROM t", "DROP TABLE t",
    "CREATE TABLE u(x)", "ALTER TABLE t ADD c", "ATTACH DATABASE ':memory:' AS m",
    "PRAGMA writable_schema=1", "VACUUM", "BEGIN", "SELECT load_extension('x')",
    "CREATE TEMP TABLE z AS SELECT 1", "REINDEX",
])
def test_mutations_rejected_and_db_unchanged(db, sql):
    before = sha(db)
    r = S.execute(db, sql)
    assert r.status in (S.REJECTED, S.ERROR), (sql, r)
    assert r.status != S.OK
    assert sha(db) == before


def test_stacked_statements_rejected(db):
    assert S.execute(db, "SELECT 1; DROP TABLE t").status == S.REJECTED
    assert S.execute(db, "").status == S.REJECTED


def test_semicolon_in_literal_allowed(db):
    r = S.execute(db, "SELECT ';' AS s -- trailing ; comment")
    assert r.status == S.OK and r.rows == [[";"]]


def test_infinite_recursion_times_out(db):
    r = S.execute(db, "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c) SELECT count(*) FROM c",
                  timeout_s=0.5)
    assert r.status == S.TIMEOUT and r.elapsed_s < 3


def test_row_cap_flags_truncation(db):
    r = S.execute(db, "SELECT * FROM t", max_rows=10)
    assert r.status == S.OK and len(r.rows) == 10 and r.truncated
    r2 = S.execute(db, "SELECT * FROM t", max_rows=100)
    assert len(r2.rows) == 100 and not r2.truncated


def test_syntax_error_is_error_not_crash(db):
    assert S.execute(db, "SELEC 1").status == S.REJECTED
    assert S.execute(db, "SELECT FROM WHERE").status == S.ERROR
    assert S.execute(db, "SELECT * FROM missing").status == S.ERROR


def test_missing_db_is_error(tmp_path):
    assert S.execute(tmp_path / "nope.sqlite", "select 1").status == S.ERROR


def test_isolated_roundtrip_and_hard_limits(db):
    r = S.execute_isolated(db, "SELECT count(*) FROM t")
    assert r.status == S.OK and r.rows == [[100]]
    r = S.execute_isolated(db, "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c) SELECT count(*) FROM c",
                           timeout_s=0.5)
    assert r.status == S.TIMEOUT
    assert S.execute_isolated(db, "DROP TABLE t").status in (S.REJECTED, S.ERROR)


def test_invalid_utf8_is_replaced_not_error(tmp_path):
    p = tmp_path / "u.sqlite"
    c = sqlite3.connect(p)
    c.execute("create table t(s text)")
    c.execute("insert into t values (cast(x'41ff42' as text))")
    c.commit(); c.close()
    r = S.execute(p, "SELECT s FROM t")
    assert r.status == S.OK and r.rows == [["A\ufffdB"]]
