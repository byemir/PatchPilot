"""Shop module (written for this project): the most recent order time as epoch seconds."""
import pandas as pd

def last_seen_epoch(stamps):
    ts = pd.to_datetime(pd.Series(stamps))
    return int(ts.astype("int64").max() // 10**9)
