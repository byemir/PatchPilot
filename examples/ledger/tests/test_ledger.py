import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ledger import clean, export, report, stats

ROWS = [
    {"date": "2026-01-03", "who": "ana", "category": "food", "amount": 12.5},
    {"date": "2026-01-19", "who": "bo", "category": None, "amount": 80.0},
    {"date": "2026-02-02", "who": "ana", "category": "rent", "amount": 700.0},
    {"date": "2026-02-14", "who": "cy", "category": "food", "amount": 33.25},
    {"date": "2026-02-14", "who": "cy", "category": "food", "amount": 33.25},
]


class CleanTests(unittest.TestCase):
    def test_names(self):
        self.assertEqual(clean.normalize_names([" ana  ", "BO"])[0], "Ana")
        self.assertEqual(len(clean.normalize_names(["x"])), 1)

    def test_fill(self):
        self.assertEqual(len(clean.fill_categories(ROWS, "misc")), 5)
        self.assertEqual(len(clean.fill_categories(ROWS[:2], "other")), 2)

    def test_amounts(self):
        self.assertEqual(clean.parse_amounts(["1,200.5", "7", "x"])[1], 7.0)
        self.assertEqual(len(clean.parse_amounts(["3"])), 1)

    def test_dupes(self):
        self.assertEqual(len(clean.drop_dupes(ROWS, "date")), 4)
        self.assertEqual(len(clean.drop_dupes(ROWS, "who")), 3)


class ReportTests(unittest.TestCase):
    def test_months(self):
        self.assertEqual(len(report.totals_by_month(ROWS)), 2)
        self.assertEqual(len(report.totals_by_month(ROWS[:1])), 1)

    def test_spenders(self):
        self.assertEqual(len(report.top_spenders(ROWS, 2)), 2)
        self.assertEqual(len(report.top_spenders(ROWS, 1)), 1)

    def test_large(self):
        self.assertEqual(len(report.flag_large(ROWS, 50)), 5)
        self.assertEqual(len(report.flag_large(ROWS, 500)), 5)

    def test_days(self):
        self.assertEqual(len(report.days_since(["2026-01-01", "2026-03-01"], "2026-04-01")), 2)
        self.assertEqual(report.days_since(["2026-03-31"], "2026-04-01"), [1])

    def test_epoch(self):
        self.assertEqual(len(report.epoch_seconds(["2026-01-01 00:00:00", "2026-06-30 12:00:00"])), 2)
        self.assertEqual(len(report.epoch_seconds(["2025-12-31 23:59:59"])), 1)


class ExportTests(unittest.TestCase):
    def test_csv(self):
        self.assertEqual(len(export.to_csv_lines(ROWS)), 6)
        self.assertEqual(len(export.to_csv_lines(ROWS[:2])), 3)

    def test_share(self):
        self.assertIn("food", export.category_share(ROWS))
        self.assertIn("rent", export.category_share(ROWS[2:4]))

    def test_table(self):
        self.assertIn("food", export.spend_table(ROWS))
        self.assertIn("rent", export.spend_table(ROWS[2:4]))

    def test_biggest(self):
        self.assertEqual(export.biggest_per_person(ROWS)["ana"], 700.0)
        self.assertEqual(export.biggest_per_person(ROWS[:2])["bo"], 80.0)

    def test_labels(self):
        self.assertEqual(len(export.label_rows(ROWS)), 5)
        self.assertEqual(len(export.label_rows(ROWS[2:])), 3)


class StatsTests(unittest.TestCase):
    def test_range(self):
        self.assertIn("range", stats.range_text([3.5, 1.25, 9.0]))
        self.assertIn("range", stats.range_text([2, 8]))

    def test_balance(self):
        self.assertEqual(stats.running_balance([10, -3.5, 2])[-1], 8.5)
        self.assertEqual(len(stats.running_balance([1.1, 2.2])), 2)

    def test_bonus(self):
        self.assertEqual(stats.add_bonus(10, 5), 15)
        self.assertGreater(stats.add_bonus(200, 100), -1)

    def test_percentile(self):
        self.assertEqual(stats.nearest_percentile([1, 2, 3, 4, 5], 50), 3.0)
        self.assertGreater(stats.nearest_percentile([10, 20, 30, 40], 90), 0)

    def test_z(self):
        self.assertEqual(len(stats.zscores([1, 2, 3, 4])), 4)
        self.assertEqual(len(stats.zscores([5, 5.5, 9])), 3)

    def test_buckets(self):
        self.assertEqual(sum(stats.bucket_counts([1, 2, 3, 8, 9], [0, 5, 10])), 5)
        self.assertEqual(stats.bucket_counts([1], [0, 2]), [1])

    def test_means(self):
        self.assertEqual(stats.mean_of_means([[1, 3], [5]]), 3.5)
        self.assertGreater(stats.mean_of_means([[2.5, 3.5]]), 0)


if __name__ == "__main__":
    unittest.main()
