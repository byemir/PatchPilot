"""Own code (written for this project): price bars as compact arrays with epoch seconds."""
import pandas as pd


def bars_to_epoch(times, close, volume):
    """Bars given as parallel lists (times as ISO strings) -> JSON-safe arrays with epoch seconds."""
    frame = pd.DataFrame({"t": pd.to_datetime(times), "c": close, "v": volume})
    return {
        "t": (frame["t"].astype("int64") // 10**9).tolist(),
        "c": [float(x) for x in frame["c"]],
        "v": [float(x) for x in frame["v"]],
    }
