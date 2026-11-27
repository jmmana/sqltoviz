import hashlib
from pathlib import Path

import duckdb
import pytest

from sqltoviz_data import sandbox as S
from sqltoviz_data import sandbox_duckdb as D


@pytest.fixture()
def db(tmp_path):
    p = tmp_path / "t.duckdb"
    c = duckdb.connect(str(p))
    c.execute("create table t as select range as a from range(100)")
    c.close()
    return p


def test_select_ok(db):
    r = D.execute(db, "SELECT sum(a) AS s FROM t")
    assert r.status == S.OK and r.rows == [[4950]] and r.columns == ["s"]


@pytest.mark.parametrize("sql", [
    "INSERT INTO t VALUES (1)", "DROP TABLE t", "CREATE TABLE u AS SELECT 1",
    "COPY t TO '/tmp/should_not_exist.csv'", "ATTACH ':memory:' AS m", "INSTALL httpfs",
    "SET enable_external_access=true", "PRAGMA enable_profiling",
])
def test_non_select_rejected_db_unchanged(db, sql):
    before = hashlib.sha256(Path(db).read_bytes()).hexdigest()
    r = D.execute(db, sql)
    assert r.status != S.OK
    assert hashlib.sha256(Path(db).read_bytes()).hexdigest() == before
    assert not Path("/tmp/should_not_exist.csv").exists()


def test_external_file_read_blocked(db):
    r = D.execute(db, "SELECT * FROM read_csv('/etc/hosts')")
    assert r.status in (S.ERROR, S.REJECTED)


def test_timeout(db):
    r = D.execute(db, "SELECT count(*) FROM range(100000000000) a, range(100000) b", timeout_s=0.5)
    assert r.status == S.TIMEOUT and r.elapsed_s < 5


def test_row_cap(db):
    r = D.execute(db, "SELECT * FROM t", max_rows=5)
    assert len(r.rows) == 5 and r.truncated
