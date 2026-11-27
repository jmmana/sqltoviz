import pytest

from sqltoviz_data import tpc

# Official TPC-H row counts at SF=0.01 (spec: customer 150k*SF, orders 1.5M*SF, supplier 10k*SF, part 200k*SF, partsupp 800k*SF).
TPCH_SF001 = {"customer": 1500, "orders": 15000, "supplier": 100, "part": 2000, "partsupp": 8000,
              "nation": 25, "region": 5}


@pytest.fixture(scope="module")
def tpch(tmp_path_factory):
    return tpc.generate("tpch", tmp_path_factory.mktemp("tpch"), 0.01)


def test_tpch_row_counts_match_spec(tpch):
    got = {t: v["rows"] for t, v in tpch["tables"].items()}
    for t, n in TPCH_SF001.items():
        assert got[t] == n, t
    assert set(got) == set(TPCH_SF001) | {"lineitem"}
    assert got["lineitem"] > 0


def test_tpch_regeneration_is_deterministic(tpch, tmp_path):
    again = tpc.generate("tpch", tmp_path, 0.01)
    assert {t: v["hash"] for t, v in again["tables"].items()} == {t: v["hash"] for t, v in tpch["tables"].items()}


def test_tpcds_generates_24_tables(tmp_path):
    m = tpc.generate("tpcds", tmp_path, 0.01)
    assert len(m["tables"]) == 24
    assert m["tables"]["store_sales"]["rows"] > 0
    assert "not a TPC Benchmark Result" in m["notice"]


def test_separate_files_avoid_name_collision(tmp_path):
    a = tpc.generate("tpch", tmp_path, 0.01)
    b = tpc.generate("tpcds", tmp_path, 0.01)
    assert a["database"] != b["database"]


def test_manifest_written_and_bad_args(tmp_path):
    tpc.generate("tpch", tmp_path, 0.01)
    assert (tmp_path / "tpch_sf0.01.manifest.json").exists()
    with pytest.raises(ValueError):
        tpc.generate("nope", tmp_path)
    with pytest.raises(ValueError):
        tpc.generate("tpch", tmp_path, 0)
