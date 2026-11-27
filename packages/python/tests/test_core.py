import unittest
from sqltoviz import recommend,to_echarts,to_vegalite,to_plotly
from sqltoviz.onnx import load_session
from tempfile import TemporaryDirectory
from pathlib import Path

class CoreTests(unittest.TestCase):
    def test_scalar(self): self.assertEqual(recommend("SELECT SUM(x)",[{"x":5}])["chartType"],"kpi")
    def test_bar(self):
        rows=[{"a":"A","v":2},{"a":"B","v":3}]
        p=recommend("SELECT a, AVG(v)",rows)
        self.assertEqual(p["chartType"],"bar")
        self.assertEqual(to_echarts(p,rows)["series"][0]["data"],[2,3])
        self.assertEqual(to_plotly(p,rows)["data"][0]["type"],"bar")
        self.assertEqual(to_vegalite(p,rows)["mark"],"bar")
    def test_line(self): self.assertEqual(recommend("SELECT d,v",[{"d":f"2026-01-0{i}","v":i} for i in range(1,5)])["chartType"],"line")
    def test_duplicate(self): self.assertEqual(recommend("SELECT a,v",[{"a":"A","v":2},{"a":"A","v":3}])["chartType"],"table")
    def test_bad_rows(self):
        for rows in [[],[{"a":1},{"b":2}],[{"a":float("inf")}],[{"a":{}}]]:
            with self.assertRaises(ValueError): recommend("SELECT a",rows)
    def test_unsafe_adapter(self):
        rows=[{"v":3}]
        with self.assertRaises(ValueError): to_echarts(recommend("SELECT v",rows),rows)
    def test_checksum(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/"model.onnx";p.write_bytes(b"invalid")
            with self.assertRaises(ValueError):load_session(p,"0"*64,kind="chart")
