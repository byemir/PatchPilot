"""Own code (written for this project): elapsed time of a sampled signal."""
import numpy as np
import pandas as pd


def elapsed_seconds(timestamps, values):
    """Seconds since the first sample for every sample, together with the values as floats."""
    index = pd.DatetimeIndex(pd.to_datetime(timestamps))
    ticks = np.array(index, dtype=np.int64)
    seconds = (ticks - ticks[0]) / 1e9
    return {"seconds": [round(float(s), 6) for s in seconds], "values": [float(v) for v in values]}
