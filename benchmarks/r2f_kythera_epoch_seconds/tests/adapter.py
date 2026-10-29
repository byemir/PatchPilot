"""Adapter (ours), read-only for the repair: JSON-friendly wrapper around the third-party function in app.py."""
import pandas as pd

from app import panel_to_compact


def compact_records(open_time, close, volume, ema_50, ema_200):
    """Adapter (ours): lists in (open_time as ISO strings), the compact dict out."""
    df = pd.DataFrame({"open_time": pd.to_datetime(open_time), "close": close, "volume": volume, "ema_50": ema_50, "ema_200": ema_200})
    return panel_to_compact(df)
