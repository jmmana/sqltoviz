import json, math, shutil, tempfile, unittest
from pathlib import Path

from sqltoviz import Engine, FeatureError, ModelError, extract_features
from sqltoviz import features as F, rules
from sqltoviz._contract import CONTRACT_SHA256, BASE_CLASSES

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "parity" / "golden_v1.json").exists())
GOLDEN = json.loads((ROOT / "parity" / "golden_v1.json").read_text())
SPEC_SHA = __import__("hashlib").sha256((ROOT / "spec" / "sqlvizspec-v1-features.json").read_bytes()).hexdigest()
try:
    import numpy, onnxruntime  # noqa: F401
    HAVE_ORT = True
except ImportError:
    HAVE_ORT = False


def close(a, b, atol, rtol):
    return abs(a - b) <= atol + rtol * abs(b)


class Features(unittest.TestCase):
    def test_contract_pin_matches_spec_bytes(self):
        self.assertEqual(CONTRACT_SHA256, SPEC_SHA)
        self.assertEqual(GOLDEN["contract_sha256"], SPEC_SHA)

    def test_all_288_cases_features_and_rejections(self):
        atol, rtol = GOLDEN["atol"], GOLDEN["rtol"]
        accepted = rejected = 0
        for c in GOLDEN["cases"]:
            exp = c["expected"]
            if exp.get("rejected"):
                with self.assertRaises(FeatureError, msg=c["case_id"]):
                    extract_features(c["sql"], c["schema"], c["rows"])
                rejected += 1
                continue
            t, cols = extract_features(c["sql"], c["schema"], c["rows"])
            self.assertEqual(len(t), 32)
            for a, b in zip(t, exp["table_features"]):
                self.assertTrue(close(a, b, atol, rtol), (c["case_id"], a, b))
            self.assertEqual(len(cols), len(exp["column_features"]))
            for ra, rb in zip(cols, exp["column_features"]):
                for a, b in zip(ra, rb):
                    self.assertTrue(close(a, b, atol, rtol), (c["case_id"], a, b))
            accepted += 1
        self.assertEqual((accepted, rejected), (sum(1 for c in GOLDEN["cases"] if not c["expected"].get("rejected")), sum(1 for c in GOLDEN["cases"] if c["expected"].get("rejected"))))
        self.assertGreaterEqual(accepted + rejected, 288)                                              # the original 288 are a prefix

    def test_constraints_and_rules_match_reference_without_models(self):
        for c in GOLDEN["cases"]:
            exp = c["expected"]
            if exp.get("rejected"):
                continue
            t, cols = extract_features(c["sql"], c["schema"], c["rows"])
            self.assertEqual(rules.rule_predict(t, cols), exp["rule_class"], c["case_id"])
            self.assertEqual(rules.eligible(t, cols), exp["eligible"], c["case_id"])
            final, changed = rules.constrained_choice(exp["chart_scores"], t, cols)
            self.assertEqual((final, changed), (exp["final_class"], exp["constraint_changed"]), c["case_id"])


@unittest.skipUnless(HAVE_ORT, "onnxruntime not installed (pip install 'sqltoviz[onnx]')")
class Models(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = Engine.default()

    def test_scores_classes_and_roles_match_golden_for_all_cases(self):
        atol, rtol = GOLDEN["atol"], GOLDEN["rtol"]
        n = 0
        for c in GOLDEN["cases"]:
            exp = c["expected"]
            if exp.get("rejected"):
                continue
            r = self.engine.recommend(c["sql"], c["schema"], c["rows"])
            for k, b in zip(BASE_CLASSES, exp["chart_scores"]):
                self.assertTrue(close(r["scores"][k], b, atol, rtol), (c["case_id"], k))
            self.assertEqual((r["base_class"], r["final_class"], r["constraint_changed"]), (exp["base_class"], exp["final_class"], exp["constraint_changed"]), c["case_id"])
            self.assertEqual([x["role"] for x in r["roles"]], exp["roles"], c["case_id"])
            for x, row in zip(r["roles"], exp["role_scores"]):
                for a, b in zip(x["scores"], row):
                    self.assertTrue(close(a, b, atol, rtol))
            n += 1
        self.assertEqual(n, sum(1 for c in GOLDEN["cases"] if not c["expected"].get("rejected")))

    def test_models_are_labelled_experimental(self):
        r = self.engine.recommend("SELECT a FROM t", ["a"], [[1.0]])
        self.assertEqual(r["model_status"], "experimental")
        self.assertTrue(any("not scientifically validated" in w for w in r["warnings"]))
        self.assertEqual(r["contract_sha256"], SPEC_SHA)

    def test_models_can_be_replaced_without_api_change(self):
        d = Path(tempfile.mkdtemp())
        src = Path(__file__).resolve().parents[1] / "sqltoviz" / "models"
        for f in ("chart_model_candidate.onnx", "role_model_candidate.onnx"):
            shutil.copy(src / f, d / ("final_" + f))
        man = {"chart": {"sha256": __import__("hashlib").sha256((d / "final_chart_model_candidate.onnx").read_bytes()).hexdigest(), "status": "validated"},
               "role": {"sha256": __import__("hashlib").sha256((d / "final_role_model_candidate.onnx").read_bytes()).hexdigest(), "status": "validated"}}
        e = Engine(d / "final_chart_model_candidate.onnx", d / "final_role_model_candidate.onnx", man)
        r = e.recommend("SELECT a FROM t", ["a"], [[1.0]])
        self.assertEqual(r["model_status"], "validated")
        self.assertFalse(any("not scientifically validated" in w for w in r["warnings"]))
        self.assertEqual(set(r), set(self.engine.recommend("SELECT a FROM t", ["a"], [[1.0]])))       # identical result shape

    def test_checksum_and_schema_enforced(self):
        d = Path(tempfile.mkdtemp())
        src = Path(__file__).resolve().parents[1] / "sqltoviz" / "models" / "chart_model_candidate.onnx"
        shutil.copy(src, d / "m.onnx")
        with self.assertRaises(ValueError):
            Engine(d / "m.onnx", None, {"chart": {"sha256": "0" * 64, "status": "x"}})
        with self.assertRaises(ModelError):
            Engine(d / "m.onnx", None, None)                                                         # no checksum supplied
        with self.assertRaises(ValueError):                                                         # chart model loaded as role model
            Engine(None, d / "m.onnx", {"role": {"sha256": __import__("hashlib").sha256(src.read_bytes()).hexdigest(), "status": "x"}})

    def test_rules_only_engine_needs_no_models(self):
        e = Engine()
        r = e.recommend("SELECT SUM(x) AS s FROM t", ["s"], [[3.0]])
        self.assertEqual((r["final_class"], r["scores"], r["roles"]), ("kpi", None, None))
        self.assertIn("rules-only", r["warnings"][0])


if __name__ == "__main__":
    unittest.main()
