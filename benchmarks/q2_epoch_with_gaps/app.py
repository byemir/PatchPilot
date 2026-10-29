"""Own code (written for this project): epoch seconds for a list of timestamp strings, with gaps kept as None."""
import pandas as pd


def epoch_with_gaps(times):
    stamps = pd.to_datetime(times)
    seconds = stamps.astype("int64") // 10**9
    return [None if pd.isna(t) else int(s) for t, s in zip(stamps, seconds)]
