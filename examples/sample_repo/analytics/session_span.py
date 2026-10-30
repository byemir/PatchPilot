"""Sample module (written for this project): length of the time range covered by a list of timestamp strings."""
import pandas as pd


def span_seconds(stamps):
    parsed = pd.to_datetime(pd.Series(stamps))
    ticks = parsed.astype("int64")
    return int((ticks.max() - ticks.min()) // 10**9)
