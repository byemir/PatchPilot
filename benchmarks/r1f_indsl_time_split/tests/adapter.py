"""Adapter (ours), read-only for the repair: JSON-friendly wrapper around the third-party function in app.py."""
import numpy as np
import pandas as pd

from app import _split_timeseries_into_time_and_value_arrays


def split_series(index, values):
    """Adapter (ours): ISO timestamps and floats in, plain lists out."""
    x, y = _split_timeseries_into_time_and_value_arrays(pd.Series(values, index=pd.DatetimeIndex(index)))
    return {"x": [round(float(v), 6) for v in x], "y": [float(v) for v in y]}
