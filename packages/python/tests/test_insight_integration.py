import unittest

from sqltoviz import recommend


class InsightIntegrationTests(unittest.TestCase):
    def test_explicit_detectors_preserve_preview_contract(self):
        rows = [{"x": x, "y": 2 * x} for x in (0, 2, 8)]
        base = recommend("SELECT x, y", rows)
        result = recommend(
            "SELECT x, y", rows, temporal_column="x", pareto_column="x",
            pareto_additive=True, correlation_columns=("x", "y"),
        )
        diagnostics = result.pop("diagnostics")
        self.assertEqual(base, result)
        self.assertEqual("zero_baseline", diagnostics["temporal"][0]["status"])
        self.assertEqual(2, diagnostics["pareto"]["items"][0]["index"])
        self.assertAlmostEqual(1.0, diagnostics["correlation"]["r"])

    def test_missing_values_and_unknown_additivity(self):
        rows = [{"x": 1}, {"x": None}, {"x": 3}]
        result = recommend("SELECT x", rows, temporal_column="x", pareto_column="x")
        self.assertTrue(all(row["status"] == "missing" for row in result["diagnostics"]["temporal"]))
        self.assertEqual("unknown_additivity", result["diagnostics"]["pareto"]["status"])

    def test_invalid_detector_columns(self):
        rows = [{"label": "A", "x": 1}]
        for options in (
            {"temporal_column": "missing"}, {"pareto_column": "label"},
            {"correlation_columns": ("x",)}, {"correlation_columns": ("x", "x")},
        ):
            with self.subTest(options=options), self.assertRaises(ValueError):
                recommend("SELECT label, x", rows, **options)
