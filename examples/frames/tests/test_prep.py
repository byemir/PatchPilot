import unittest

import pandas as pd

from frames import prep


def sample():
    return pd.DataFrame({
        "name": [" Ada ", "Bob", "Cy", "Di"],
        "age": [30.0, None, 41.0, 25.0],
        "income": [5200.0, 4100.0, None, 9900.0],
        "signup": ["2024-03-01 10:00:00", "2024-03-02 11:30:00", "2024-04-05 08:15:00", "2024-05-06 09:00:00"],
    })


class PrepTests(unittest.TestCase):
    def test_fill_missing(self):
        out = prep.fill_missing(sample())
        self.assertEqual(out["age"].tolist(), [30.0, 30.0, 41.0, 25.0])
        self.assertEqual(out["income"].tolist(), [5200.0, 4100.0, 0.0, 9900.0])

    def test_flag_outliers(self):
        out = prep.flag_outliers(sample(), 9000)
        self.assertEqual(out["outlier"].tolist(), [0, 0, 0, 1])

    def test_signup_seconds(self):
        self.assertEqual(prep.add_signup_seconds(sample())["signup_s"].iloc[0], 1709287200)

    def test_income_per_age(self):
        self.assertEqual(prep.income_per_age(sample())["ratio"].round(1).iloc[0], 173.3)

    def test_top_earners(self):
        self.assertEqual(prep.top_earners(sample(), 2)["name"].tolist(), ["Di", " Ada "])

    def test_clean_names(self):
        self.assertEqual(prep.clean_names(sample())["name"].tolist(), ["ada", "bob", "cy", "di"])


if __name__ == "__main__":
    unittest.main()
