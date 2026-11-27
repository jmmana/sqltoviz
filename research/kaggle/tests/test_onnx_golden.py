import json

import numpy as np
import pytest

from sqltoviz_data import experiment as E
from sqltoviz_data import golden as G
from sqltoviz_data import onnx_export as OX
from sqltoviz_data import synthgen as SG


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    items = SG.generate(80, seed=2, n_schemas=40)
    X, _ = E.featurize(items)
    y = [i["label"] for i in items]
    m = OX.fit_contract_model(X, y, seed=0, n_estimators=30)
    p = OX.export_chart_model(m, tmp_path_factory.mktemp("m") / "chart.onnx")
    return items, X, m, p


def test_export_io_contract_and_parity_with_sklearn(trained):
    items, X, m, p = trained
    import onnx
    g = onnx.load(str(p)).graph
    assert [i.name for i in g.input] == ["table_features"] and [o.name for o in g.output] == ["chart_scores"]
    sess = OX.session(p)
    assert sess.get_inputs()[0].shape[1] == 32 and sess.get_outputs()[0].shape[1] == 10
    v = OX.verify_against_sklearn(m, sess, X)
    assert v["within_tolerance"] and v["argmax_equal_rate"] == 1.0 and v["row_sums_max_dev"] < 1e-5, v
    meta = {x.key: x.value for x in onnx.load(str(p)).metadata_props}
    assert meta["contract_sha256"] == OX.F.CONTRACT_SHA256 and json.loads(meta["class_order"]) == list(OX.CLASSES)


def test_class_order_is_contract_order(trained):
    items, X, m, p = trained
    sess = OX.session(p)
    kpi_rows = [k for k, i in enumerate(items) if i["label"] == "kpi"]
    pred = OX.predict_onnx(sess, X[kpi_rows]).argmax(1)
    assert (pred == OX.CLASSES.index("kpi")).mean() > 0.9     # column 0 is kpi, not alphabetical 'area'


def test_training_requires_all_classes():
    X = np.zeros((4, 32), dtype=np.float32)
    with pytest.raises(ValueError):
        OX.fit_contract_model(X, ["kpi", "bar", "kpi", "bar"])
    with pytest.raises(ValueError):
        OX.fit_contract_model(np.zeros((4, 31)), ["kpi"] * 4)


def test_golden_build_verify_roundtrip_and_tamper_detection(trained):
    items, X, m, p = trained
    sess = OX.session(p)
    cases = G.handcrafted_cases() + G.synthetic_cases(items, per_class=5, seed=1)
    g = G.build_golden(cases, sess)
    assert g["n_cases"] == len(cases) and {c["case_id"] for c in g["cases"]} == {c["case_id"] for c in cases}
    rep = G.verify_golden(json.loads(json.dumps(g)), sess)      # survives JSON round trip (NaN/inf cleaned)
    assert rep["failures"] == [] and rep["rejected_ok"] == sum(1 for c in cases if c["expect"] == "reject")
    bad = json.loads(json.dumps(g))
    k = next(i for i, c in enumerate(bad["cases"]) if "table_features" in c["expected"])
    bad["cases"][k]["expected"]["table_features"][0] += 1e-3
    assert G.verify_golden(bad, sess)["failures"]


def test_handcrafted_cases_cover_rejections_and_edge_kinds():
    cs = G.handcrafted_cases()
    assert sum(c["expect"] == "reject" for c in cs) >= 10 and sum(c["expect"] == "accept" for c in cs) >= 25
    assert len({c["case_id"] for c in cs}) == len(cs)


def test_role_model_export_parity_and_order(tmp_path):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(300, 28)).astype(np.float32)
    y = [OX.ROLES[int(abs(X[i, 0] * 2) + (X[i, 1] > 0)) % 5] for i in range(300)]
    m = OX.fit_role_model(X, y, n_estimators=20)
    p = OX.export_role_model(m, tmp_path / "role.onnx")
    sess = OX.session(p)
    got = OX.predict_roles_onnx(sess, X[:7])               # dynamic M rows, any M
    ref = m.predict_proba(X[:7])
    assert got.shape == (7, 5) and np.allclose(got, ref, atol=1e-6)
    assert OX.predict_roles_onnx(sess, X[:1]).shape == (1, 5)
    with pytest.raises(ValueError):
        OX.fit_role_model(X[:10], ["x_axis"] * 10)


def test_training_and_export_are_byte_reproducible(tmp_path):
    items = SG.generate(40, seed=4, n_schemas=20)
    X, _ = E.featurize(items)
    y = [i["label"] for i in items]
    hashes = []
    for k in range(2):
        m = OX.fit_contract_model(X, y, seed=0, n_estimators=10)
        hashes.append(OX.sha256_file(OX.export_chart_model(m, tmp_path / f"m{k}.onnx")))
    assert hashes[0] == hashes[1]
