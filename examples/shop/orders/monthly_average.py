"""Shop module (written for this project): average order value per month, as text keys."""
import pandas as pd

def monthly_average(rows):
    df = pd.DataFrame(rows)
    df["ts"] = pd.to_datetime(df["ts"])
    monthly = df.set_index("ts")["amount"].resample("M").mean()
    return {d.strftime("%Y-%m"): round(float(v), 2) for d, v in monthly.items()}
