import hashlib, json, unittest
from pathlib import Path

from sqltoviz import normalize_output, resolve_column_types, specialize_outputs
from sqltoviz import _outputs as O
from sqltoviz import outputs as impl
from sqltoviz._contract import BASE_CLASSES, CONTRACT_SHA256

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "parity" / "outputs_v1.json").exists())
SPEC_BYTES = (ROOT / "spec" / "sqlvizspec-v1-outputs.json").read_bytes()
SPEC = json.loads(SPEC_BYTES)
FIX = json.loads((ROOT / "parity" / "outputs_v1.json").read_text())
ATOL, RTOL = FIX["atol"], FIX["rtol"]


def close(a, b):
    return abs(a - b) <= ATOL + RTOL * abs(b)


def assert_same(tc, a, b, path=""):
    """Structural equality; floats at atol=rtol=1e-6."""
    if isinstance(b, bool) or isinstance(a, bool) or not (isinstance(b, float) or isinstance(a, float)):
        if isinstance(b, dict):
            tc.assertEqual(set(a), set(b), path)
            for k in b:
                assert_same(tc, a[k], b[k], f"{path}.{k}")
        elif isinstance(b, list):
            tc.assertEqual(len(a), len(b), path)
            for i, (x, y) in enumerate(zip(a, b)):
                assert_same(tc, x, y, f"{path}[{i}]")
        else:
            tc.assertEqual(a, b, path)
    else:
        tc.assertTrue(close(a, b), f"{path}: {a} vs {b}")


class Contract(unittest.TestCase):
    def test_pins(self):
        self.assertEqual(O.OUTPUTS_SHA256, hashlib.sha256(SPEC_BYTES).hexdigest())
        self.assertEqual(O.BASE_CONTRACT_SHA256, CONTRACT_SHA256)
        self.assertEqual(SPEC["base_contract_sha256"], CONTRACT_SHA256)
        self.assertEqual(FIX["outputs_sha256"], O.OUTPUTS_SHA256)
        self.assertEqual(FIX["base_contract_sha256"], CONTRACT_SHA256)

    def test_base_contract_untouched(self):
        self.assertEqual(hashlib.sha256((ROOT / "spec" / "sqlvizspec-v1-features.json").read_bytes()).hexdigest(),
                         "d14d140b9118c0b535d4e504af7f16546f47d56ac8f1692c2ab62615686e5864")

    def test_21_outputs_and_map(self):
        self.assertEqual(len(O.OUTPUTS), 21)
        self.assertEqual(set(O.SPECIALIZATION), set(BASE_CLASSES))
        self.assertEqual({o for v in O.SPECIALIZATION.values() for o in v}, set(O.OUTPUTS))
        self.assertEqual(O.SPECIALIZATION["bar"], ["waterfall", "grouped_bar", "treemap", "violin", "boxplot", "histogram", "bar"])
        self.assertEqual(normalize_output("kpi_card"), "kpi")

    def test_every_precondition_is_implemented_and_reasons_declared(self):
        ids = {p["id"] for d in O.DEFINITIONS.values() for p in d["preconditions"]}
        self.assertEqual(ids, set(impl.CHECKS))
        self.assertTrue({p["reason"] for d in O.DEFINITIONS.values() for p in d["preconditions"]} <= set(O.REASON_CODES))
        for o in ("histogram", "boxplot", "violin"):
            self.assertFalse(O.DEFINITIONS[o]["requires_base_eligibility"])
            self.assertNotIn("base_eligible", [p["id"] for p in O.DEFINITIONS[o]["preconditions"]])
        for o in set(O.OUTPUTS) - {"histogram", "boxplot", "violin", "table"}:
            self.assertEqual(O.DEFINITIONS[o]["preconditions"][0]["id"], "base_eligible")

    def test_fixtures_are_current(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("gen_outputs", ROOT / "parity" / "tools" / "gen_outputs.py")
        g = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(g)
        self.assertEqual(json.dumps(g.build(), indent=1, ensure_ascii=False) + "\n", (ROOT / "parity" / "outputs_v1.json").read_text())


class Fixtures(unittest.TestCase):
    def test_every_output_has_positive_and_negative_or_edge(self):
        for o in O.OUTPUTS:
            s = FIX["support_per_output"][o]
            self.assertGreaterEqual(s["positive"], 1, o)
            self.assertGreaterEqual(s["negative"] + s["edge"], 1, o)
        self.assertEqual(FIX["n_cases"], len(FIX["cases"]))

    def test_replay(self):
        for c in FIX["cases"]:
            with self.subTest(c["id"]):
                r = specialize_outputs(c["columns"], c["rows"], c["metadata"], c["base_scores"], c["roles"], c["base_eligibility"])
                assert_same(self, r, c["expected"], c["id"])
                if c["kind"] == "positive":
                    self.assertEqual(r["output"], c["target"])
                self.assertEqual(r["fallback_chain"][-1], r["output"])
                self.assertEqual(len(set(r["fallback_chain"])), len(r["fallback_chain"]))

    def test_resolution_is_idempotent(self):
        c = FIX["cases"][0]
        self.assertEqual(resolve_column_types(c["columns"], c["rows"]), c["columns"])


class Behaviour(unittest.TestCase):
    el = {b: True for b in BASE_CLASSES}

    def test_absent_metadata_fails_closed(self):
        rows = [[f"2024-01-0{i}", float(i), float(i * 10)] for i in range(1, 6)]
        r = specialize_outputs([{"name": "d"}, {"name": "a"}, {"name": "b"}], rows, None, {"line": 1}, None, self.el)
        self.assertEqual(r["output"], "line")
        self.assertIn({"output": "combo_dual_axis", "reason_code": "measures_not_declared"}, r["rejected"])

    def test_dual_axis_ignores_scale_ratio(self):
        meta = {"columns": {"a": {"unit": "u", "axis": "left", "label": "A"}, "b": {"unit": "v", "axis": "right", "label": "B"}}}
        for scale in (2.0, 1e-9, 1e12):
            rows = [[f"2024-01-0{i}", float(i), scale * i] for i in range(1, 6)]
            self.assertEqual(specialize_outputs([{"name": "d"}, {"name": "a"}, {"name": "b"}], rows, meta, {"line": 1}, None, self.el)["output"], "combo_dual_axis")

    def test_tolerance_boundary_waterfall(self):
        meta = {"columns": {"v": {"additive": True}}, "waterfall": {"order_by": "s", "total": 3.0 + 5e-7}}
        r = specialize_outputs([{"name": "s"}, {"name": "v"}], [["a", 1.0], ["b", 2.0]], meta, {"bar": 1}, None, self.el)
        self.assertEqual(r["output"], "waterfall")
        meta["waterfall"]["total"] = 3.0 + 1e-5
        self.assertNotEqual(specialize_outputs([{"name": "s"}, {"name": "v"}], [["a", 1.0], ["b", 2.0]], meta, {"bar": 1}, None, self.el)["output"], "waterfall")

    def test_gate_skipped_only_for_raw_samples(self):
        rows = [[float(i)] for i in range(40)]
        none = {b: False for b in BASE_CLASSES}
        r = specialize_outputs([{"name": "x"}], rows, {"raw_samples": True}, {"bar": 1}, None, none)
        self.assertEqual(r["output"], "histogram")
        r = specialize_outputs([{"name": "x"}], rows, None, {"bar": 1}, None, none)
        self.assertEqual(r["output"], "table")
        self.assertEqual(r["fallback_chain"][-1], "table")

    def test_known_numbers(self):
        rows = [["g", v] for v in (1.0, 2.0, 2.0, 3.0, 3.0, 4.0, 100.0)] + [["h", v] for v in (1.0, 2.0, 3.0, 4.0, 5.0)]
        r = specialize_outputs([{"name": "g"}, {"name": "v"}], rows, {"raw_samples": {"column": "v", "group": "g"}}, {"bar": 1}, None, self.el)
        g = r["params"]["groups"][0]
        self.assertEqual((g["q1"], g["median"], g["q3"], g["whisker_high"], g["outliers"]), (2.0, 3.0, 3.5, 4.0, 1))
        h = r["params"]["groups"][1]
        self.assertEqual((h["q1"], h["median"], h["q3"]), (2.0, 3.0, 4.0))


if __name__ == "__main__":
    unittest.main()
