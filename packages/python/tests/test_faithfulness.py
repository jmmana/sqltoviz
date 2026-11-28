"""Replay parity/tools/gen_faithfulness.py cases (set SQLTOVIZ_FAITH=<file>); errors are measured against exact rational/decimal references."""
import json, os, unittest
from sqltoviz import statistics as S


def rel(a, b):
    return abs(a - b) / max(abs(b), 1e-300)


@unittest.skipUnless(os.environ.get("SQLTOVIZ_FAITH") and os.path.exists(os.environ.get("SQLTOVIZ_FAITH", "")), "set SQLTOVIZ_FAITH to a file from parity/tools/gen_faithfulness.py")
class Faithfulness(unittest.TestCase):
    def test_detectors_match_exact_references(self):
        G = json.load(open(os.environ["SQLTOVIZ_FAITH"])); tol = G["tolerance"]; worst = {"mad": 0.0, "pearson": 0.0, "temporal": 0.0, "pareto": 0.0}
        for c in G["cases"]:
            e, k = c["expected"], c["kind"]
            if k == "mad":
                r = S.mad_outliers(c["values"]); self.assertEqual(r["status"], e["status"])
                if e["status"] in ("ok", "zero_mad"): worst[k] = max(worst[k], rel(r["median"], e["median"]) if e["median"] else abs(r["median"]), rel(r["mad"], e["mad"]) if e["mad"] else abs(r["mad"]))
                self.assertEqual([o["index"] for o in r["outliers"]], [o["index"] for o in e["outliers"]])
                for o, p in zip(r["outliers"], e["outliers"]): worst[k] = max(worst[k], rel(o["score"], p["score"]))
            elif k == "pearson":
                r = S.pearson(c["xs"], c["ys"]); self.assertEqual(r["status"], e["status"])
                if e["status"] == "ok": worst[k] = max(worst[k], abs(r["r"] - e["r"]))
            elif k == "temporal":
                r = S.temporal_shifts(c["values"]); self.assertEqual([x["status"] for x in r], [x["status"] for x in e])
                for x, y in zip(r, e):
                    if y["delta"] is not None: worst[k] = max(worst[k], rel(x["delta"], y["delta"]) if y["delta"] else abs(x["delta"]))
                    if y["relative_change"] is not None: worst[k] = max(worst[k], rel(x["relative_change"], y["relative_change"]) if y["relative_change"] else abs(x["relative_change"]))
            else:
                r = S.pareto(c["values"], c["coverage"], additive=True); self.assertEqual(r["status"], e["status"])
                self.assertEqual([i["index"] for i in r["items"]], [i["index"] for i in e["items"]]); self.assertEqual([i["included"] for i in r["items"]], [i["included"] for i in e["items"]])
                for x, y in zip(r["items"], e["items"]): worst[k] = max(worst[k], abs(x["share"] - y["share"]), abs(x["cumulative"] - y["cumulative"]))
        print("python worst errors", worst)
        self.assertLess(max(worst["mad"], worst["temporal"]), tol["relative"]); self.assertLess(worst["pearson"], tol["pearson_abs"]); self.assertLess(worst["pareto"], 1e-12)


if __name__ == "__main__":
    unittest.main()
