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


if __name__ == "__main__":
    unittest.main()
