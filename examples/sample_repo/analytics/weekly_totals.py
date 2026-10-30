"""Sample module (written for this project): totals per week number. Behaves the same on pandas 2.3 and 3.0."""
import pandas as pd


def weekly_totals(weeks, amounts):
    table = pd.DataFrame({"week": weeks, "amount": amounts})
    sums = table.groupby("week")["amount"].sum()
    return {int(k): int(v) for k, v in sums.items()}
