import unittest
from sqltoviz.statistics import mad_outliers, temporal_shifts, pareto, pearson

class StatisticsTests(unittest.TestCase):
    def test_mad(self):
        self.assertEqual(mad_outliers([1,2,3,4,100])["outliers"][0]["index"],4)
    def test_zero_mad(self):
        self.assertEqual(mad_outliers([1,1,1,100])["status"],"zero_mad")
    def test_missing_mad(self):
        self.assertEqual(mad_outliers([None,1,float("nan")])["status"],"insufficient_samples")
    def test_temporal(self):
        r=temporal_shifts([0,10,None,20,10])
        self.assertEqual([x["status"] for x in r],["zero_baseline","missing","missing","ok"])
        self.assertAlmostEqual(r[-1]["relative_change"],-.5)
    def test_negative_baseline(self):
        self.assertEqual(temporal_shifts([-10,-5])[0]["relative_change"],.5)
    def test_pareto(self):
        r=pareto([20,80,0],additive=True)
        self.assertEqual([x["index"] for x in r["items"] if x["included"]],[1])
    def test_pareto_invalid(self):
        self.assertEqual(pareto([1,2])["status"],"unknown_additivity")
        self.assertEqual(pareto([1,-2],additive=True)["status"],"invalid_weights")
        self.assertEqual(pareto([0,0],additive=True)["status"],"zero_total")
    def test_pearson(self):
        self.assertAlmostEqual(pearson([1,2,None,3],[3,2,8,1])["r"],-1)
        self.assertEqual(pearson([1,1,1],[1,2,3])["status"],"constant_column")
    def test_pearson_extremes(self):
        self.assertAlmostEqual(pearson([-1e308,0,1e308],[-1e308,0,1e308])["r"],1)
    def test_invalid(self):
        with self.assertRaises(ValueError): pearson([1],[1,2])
        with self.assertRaises(ValueError): mad_outliers([1,2,3],0)
