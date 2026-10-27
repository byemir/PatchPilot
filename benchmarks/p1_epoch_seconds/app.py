import pandas as pd


def to_epoch_seconds(timestamps):
    """Convert timestamp strings to integer Unix seconds."""
    ts = pd.to_datetime(list(timestamps))
    return (ts.astype("int64") // 10**9).tolist()
