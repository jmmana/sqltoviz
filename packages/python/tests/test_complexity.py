"""Complexity guard (#36): feature extraction is O(N log N) (exact median/quantiles sort each quantitative column); an accidental O(N^2) would
make a 10x larger input ~100x slower. The bound below (< 40x) is far from the expected ~10-13x and robust to CI noise."""
import time
import unittest

from sqltoviz import extract_features

SQL = "SELECT category, region, SUM(value) AS value, day FROM t GROUP BY category, region, day ORDER BY day"
SCHEMA = [{"name": "category"}, {"name": "region"}, {"name": "value"}, {"name": "day"}]


def rows(n):
    return [[f"cat{(i * 7) % 12}", f"reg{(i * 3) % 5}", ((i * 37) % 1000) + ((i * 13) % 100) / 100, f"2024-{1 + i % 12:02d}-{1 + i % 27:02d}"] for i in range(n)]


def best(n, reps=5):
    r = rows(n)
    ts = []
    for _ in range(reps):
        t = time.perf_counter()
        extract_features(SQL, SCHEMA, r)
        ts.append(time.perf_counter() - t)
    return min(ts)


class Complexity(unittest.TestCase):
    def test_extraction_scales_near_linearly(self):
        small, large = best(2000), best(20000)
        self.assertLess(large / small, 40, f"10x rows took {large / small:.1f}x longer (expected about 10-13x)")


if __name__ == "__main__":
    unittest.main()
