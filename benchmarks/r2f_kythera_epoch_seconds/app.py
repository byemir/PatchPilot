"""Third-party code. The function panel_to_compact is copied verbatim (by scripts/build_real_case.py, with ast) from
https://github.com/ziagl888/Kythera/blob/d0ff0159d9ae429fffffa93a800479e960b04614/tools/breadth_study.py
(parent of merge commit e3181d5aeb of https://github.com/ziagl888/Kythera/pull/229), license MIT. See docs/THIRD_PARTY_NOTICES.md.
The adapter (ours) is in tests/adapter.py and is read-only for the repair.
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
