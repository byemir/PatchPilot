"""Shop module (written for this project): replaces a missing region with 'unknown' and returns the column."""
import pandas as pd

def fill_missing_region(rows):
    df = pd.DataFrame(rows)
    df["region"].fillna("unknown", inplace=True)
    return df["region"].tolist()
