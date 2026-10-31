"""Stock tables. Imports its sibling module, as real code does (written for this repository)."""
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
