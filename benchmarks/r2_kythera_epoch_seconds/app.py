"""Third-party code. The function panel_to_compact is copied verbatim (by scripts/build_real_case.py, with ast) from
https://github.com/ziagl888/Kythera/blob/d0ff0159d9ae429fffffa93a800479e960b04614/tools/breadth_study.py
(parent of merge commit e3181d5aeb of https://github.com/ziagl888/Kythera/pull/229), license MIT. See docs/THIRD_PARTY_NOTICES.md.
Everything under the marker "adapter (ours)" was written for this project.
"""
import pandas as pd


def panel_to_compact(df: pd.DataFrame) -> dict:
    """A loaded per-coin panel → JSON-safe compact arrays (epoch-seconds + floats)."""
    return {
        "t": (df["open_time"].astype("int64") // 10**9).tolist(),
        "c": df["close"].tolist(),
        "v": df["volume"].tolist(),
        "e50": df["ema_50"].tolist(),
        "e200": df["ema_200"].tolist(),
    }


# --- adapter (ours) ---
def compact_records(open_time, close, volume, ema_50, ema_200):
    """Adapter (ours): lists in (open_time as ISO strings), the compact dict out."""
    df = pd.DataFrame({"open_time": pd.to_datetime(open_time), "close": close, "volume": volume, "ema_50": ema_50, "ema_200": ema_200})
    return panel_to_compact(df)
