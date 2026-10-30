"""Shop module (written for this project): revenue per calendar day from order rows."""
import pandas as pd

def daily_revenue(rows):
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"])
    per_day = df.groupby(df["ts"].dt.date)["amount"].sum()
    return {str(day): round(float(v), 2) for day, v in per_day.items()}
