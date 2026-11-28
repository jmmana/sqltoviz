import unittest

from sqltoviz import recommend, to_echarts, to_plotly, to_vegalite


class AdapterTests(unittest.TestCase):
    def test_horizontal_bar_preserves_category_order_and_measure(self):
        rows = [{"label": f"Group {i}", "value": -i} for i in range(13)]
        plan = recommend("SELECT label, value FROM results", rows)
        self.assertEqual("horizontal_bar", plan["chartType"])
        echarts = to_echarts(plan, rows)
        self.assertEqual("value", echarts["xAxis"]["name"])
        self.assertEqual([row["label"] for row in rows], echarts["yAxis"]["data"])
        vega = to_vegalite(plan, rows)
        self.assertEqual({"field": "value", "type": "quantitative"}, vega["encoding"]["x"])
        self.assertEqual("label", vega["encoding"]["y"]["field"])
        plotly = to_plotly(plan, rows)["data"][0]
        self.assertEqual("h", plotly["orientation"])
        self.assertEqual([row["value"] for row in rows], plotly["x"])

    def test_line_preserves_temporal_encoding(self):
        rows = [{"day": f"2026-01-0{i}", "total": i} for i in range(1, 5)]
        plan = recommend("SELECT day, total FROM results", rows)
        self.assertEqual("line", to_echarts(plan, rows)["series"][0]["type"])
        self.assertEqual("temporal", to_vegalite(plan, rows)["encoding"]["x"]["type"])
        self.assertEqual("lines+markers", to_plotly(plan, rows)["data"][0]["mode"])

    def test_non_chart_plans_are_rejected_by_all_adapters(self):
        for rows in ([{"value": 1}], [{"value": "label"}]):
            plan = recommend("SELECT value FROM results", rows)
            for adapt in (to_echarts, to_vegalite, to_plotly):
                with self.subTest(adapter=adapt.__name__, chart=plan["chartType"]):
                    with self.assertRaises(ValueError):
                        adapt(plan, rows)
