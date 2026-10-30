"""Shop module (written for this project): marks orders above a limit and returns the flags in row order."""
import pandas as pd

def flag_big_orders(rows, limit):
    df = pd.DataFrame(rows)
    df["big"] = False
    df["big"][df["amount"] > limit] = True
    return df["big"].tolist()
