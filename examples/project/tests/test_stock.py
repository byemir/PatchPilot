import unittest

import pandas as pd

from inv import stock


def sample():
    return pd.DataFrame({"item": ["bolt", "bulk_nut", "gear", "belt"], "qty": [3, 12, 1, 7]})


class StockTests(unittest.TestCase):
    def test_flag_low(self):
        self.assertEqual(stock.flag_low(sample())["low"].tolist(), [True, False, True, False])

    def test_reorder_plan(self):
        self.assertEqual(stock.reorder_plan(sample())["order"].tolist(), [7, 8, 9, 3])

    def test_span_seconds(self):
        s = pd.Series([1, 2, 3], index=pd.to_datetime(["2024-03-01 10:00:00", "2024-03-01 11:00:00", "2024-03-01 12:00:00"]))
        self.assertEqual(stock.span_seconds(s), 7200.0)

    def test_elapsed_and_values(self):
        s = pd.Series([1.0, 2.0, 4.0], index=pd.to_datetime(["2024-03-01 10:00:00", "2024-03-01 11:00:00", "2024-03-01 12:30:00"]))
        x, y = stock.elapsed_and_values(s)
        self.assertEqual(x.tolist(), [0.0, 3600.0, 9000.0])
        self.assertEqual(y.tolist(), [1.0, 2.0, 4.0])


if __name__ == "__main__":
    unittest.main()
