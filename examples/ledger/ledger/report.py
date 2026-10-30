import pandas as pd


def totals_by_month(rows):
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    g = df.groupby(df["date"].dt.to_period("M"))["amount"].sum()
    return {str(k): float(v) for k, v in g.items()}


def top_spenders(rows, n):
    df = pd.DataFrame(rows)
    return df.groupby("who")["amount"].sum().sort_values(ascending=False).head(n).to_dict()


def flag_large(rows, limit):
    df = pd.DataFrame(rows)
    df["large"] = False
    df["large"][df["amount"] > limit] = True
    return df["large"].tolist()


def days_since(dates, today):
    s = pd.to_datetime(pd.Series(dates))
    return (pd.Timestamp(today) - s).dt.days.tolist()


def epoch_seconds(dates):
    s = pd.to_datetime(pd.Series(dates))
    return (s.astype("int64") // 10**9).tolist()
