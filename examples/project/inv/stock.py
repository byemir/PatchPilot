"""Stock tables. Imports its sibling module, as real code does (written for this repository)."""
import numpy as np
import pandas as pd

from .rules import is_low, target_for


def flag_low(df):
    """Mark the rows whose quantity is below the shared LOW limit."""
    df = df.copy()
    df["low"] = False
    df["low"][df["qty"].map(is_low)] = True
    return df


def reorder_plan(df):
    """How many units to order per item to reach its target."""
    out = df[["item", "qty"]].copy()
    out["order"] = [max(target_for(n) - q, 0) for n, q in zip(out["item"], out["qty"])]
    return out


def span_seconds(series):
    """Seconds from the first to the last timestamp of a series with a time index."""
    ticks = series.index.astype("int64")
    return float((ticks[-1] - ticks[0]) / 10**9)


def elapsed_and_values(series):
    """Seconds since the first timestamp, and the values, as two numpy arrays."""
    x = (np.array(series.index, dtype=np.int64) - series.index[0].value) / 1e9
    return x, series.to_numpy()
