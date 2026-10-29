import pandas as pd


def session_report(events, cutoff):
    """Summarise user events.

    events: [{"user": ..., "ts": "YYYY-MM-DD HH:MM:SS" (UTC, naive), "amount": ..., "note": text or null}, ...].
    Returns the rows [user, epoch seconds, flag] ("large" when amount > cutoff, else "ok"), the positions of the events
    whose note is null, and the last epoch seconds.
    """
    df = pd.DataFrame(events, columns=["user", "ts", "amount", "note"])
    df["ts"] = pd.to_datetime(df["ts"])
    df["epoch"] = df["ts"].astype("int64") // 10**9
    df["flag"] = "ok"
    big = df["amount"] > cutoff
    df["flag"][big] = "large"
    missing = [i for i, v in enumerate(df["note"]) if v is None]
    rows = [[str(r.user), int(r.epoch), str(r.flag)] for r in df.itertuples()]
    return {"rows": rows, "missing_notes": missing, "last_epoch": int(df["epoch"].max())}
