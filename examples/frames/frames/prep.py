"""Table preparation in the style of a notebook that became a module. Written for this repository; each function takes
and returns a pandas DataFrame."""
import numpy as np
import pandas as pd


def fill_missing(df):
    """Fill missing ages with the median and missing incomes with zero."""
    df = df.copy()
    df["age"].fillna(df["age"].median(), inplace=True)
    df["income"].fillna(0, inplace=True)
    return df


def flag_outliers(df, limit):
    """Mark rows whose income is above the limit."""
    df = df.copy()
    df["outlier"] = 0
    df["outlier"][df["income"] > limit] = 1
    return df


def add_signup_seconds(df):
    """Seconds since 1970-01-01 for each signup time."""
    df = df.copy()
    df["signup_s"] = pd.to_datetime(df["signup"]).astype("int64") // 10**9
    return df


def income_per_age(df):
    """Income divided by age, rounded to 2 decimals (rows with age 0 stay empty)."""
    out = df[["name", "age", "income"]].copy()
    ratio = out["income"] / out["age"].replace(0, np.nan)
    out["ratio"] = ratio.round(2)
    return out


def top_earners(df, n):
    """The n highest incomes, name and income only."""
    return df.sort_values("income", ascending=False).head(n)[["name", "income"]].reset_index(drop=True)


def clean_names(df):
    """Strip and lower-case the names."""
    df = df.copy()
    df["name"] = df["name"].str.strip().str.lower()
    return df
