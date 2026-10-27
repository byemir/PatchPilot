import pandas as pd


def schedule(start, tz, n_days, count):
    """Repeat a job every `n_days` days from `start` (local time in `tz`).

    Returns local timestamps as strings, once computed one by one and once for a whole index.
    """
    t0 = pd.Timestamp(start).tz_localize(tz)
    step = pd.offsets.Day(n_days)
    one_by_one = [(t0 + k * step).strftime("%Y-%m-%d %H:%M %z") for k in range(count)]
    index = pd.DatetimeIndex([t0] * count) + step
    as_index = [t.strftime("%Y-%m-%d %H:%M %z") for t in index]
    return {"one_by_one": one_by_one, "as_index": as_index}
