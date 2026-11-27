import json
from pathlib import Path
import unittest
from sqltoviz import recommend,mad_outliers,temporal_shifts,pareto,pearson
F=json.loads((Path(__file__).resolve().parents[3]/"parity/preview-v0.1.json").read_text(encoding="utf-8"))
class PreviewParity(unittest.TestCase):
 def test_charts(self):
  for c in F["charts"]:
   with self.subTest(c=c["id"]):
    p=recommend(c["sql"],c["rows"])
    self.assertEqual((p["chartType"],p["encodings"].get("x"),p["encodings"].get("y")),(c["chart"],c.get("x"),c.get("y")))
 def test_statistics(self):
  s=F["statistics"]
  for c in s["mad"]:
   p=mad_outliers(c["values"]);self.assertEqual(p["status"],c["status"]);self.assertEqual([x["index"] for x in p["outliers"]],c["indices"])
  for c in s["temporal"]:
   p=temporal_shifts(c["values"]);self.assertEqual([x["status"] for x in p],c["statuses"]);self.assertEqual([x["relative_change"] for x in p],c["changes"])
  for c in s["pareto"]:
   p=pareto(c["values"],additive=c["additive"]);self.assertEqual(p["status"],c["status"]);self.assertEqual([x["index"] for x in p["items"] if x["included"]],c["indices"])
  for c in s["pearson"]:
   p=pearson(c["xs"],c["ys"]);self.assertEqual(p["status"],c["status"])
   if c["r"] is None:self.assertIsNone(p["r"])
   else:self.assertAlmostEqual(p["r"],c["r"],delta=F["tolerance"])
