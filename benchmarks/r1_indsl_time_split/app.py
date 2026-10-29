"""Third-party code. The function _split_timeseries_into_time_and_value_arrays is copied verbatim (by scripts/build_real_case.py, with ast) from
https://github.com/cognitedata/indsl/blob/fab55f6dfa8278050a841fc38f57e692504cfeb4/indsl/data_quality/outliers.py
(parent of merge commit 5ec4a2ed4f of https://github.com/cognitedata/indsl/pull/639), license Apache-2.0. See docs/THIRD_PARTY_NOTICES.md.
Everything under the marker "adapter (ours)" was written for this project.
"""
import numpy as np
import pandas as pd


def _split_timeseries_into_time_and_value_arrays(data: pd.Series) -> tuple:
    """Split ts into time and value arrays.

    Method that takes a time series with a datetime index and splits it into two numpy arrays. One with the datetime
    index converted to integer values, starting from zero, and the other array contains the values of the time series.

    Args:
        data (pandas.Seres): Time series with a datetime index

    Returns:
        tuple: Tuple containing two 1-D numpy arrays:
            x -> Datetime index converted to integers starting at 0
            y -> Time series values
    """
    x = (np.array(data.index, dtype=np.int64) - data.index[0].value) / 1e9
    y = data.to_numpy()  # Just to please pandas devs
    return x, y


# --- adapter (ours) ---
def split_series(index, values):
    """Adapter (ours): ISO timestamps and floats in, plain lists out."""
    x, y = _split_timeseries_into_time_and_value_arrays(pd.Series(values, index=pd.DatetimeIndex(index)))
    return {"x": [round(float(v), 6) for v in x], "y": [float(v) for v in y]}
