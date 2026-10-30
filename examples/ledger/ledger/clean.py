import pandas as pd


def normalize_names(names):
    s = pd.Series(names)
    return s.str.strip().str.title().tolist()


def fill_categories(rows, default):
    df = pd.DataFrame(rows)
    df["category"].fillna(default, inplace=True)
    return df["category"].tolist()


def parse_amounts(texts):
    s = pd.Series(texts).str.replace(",", "", regex=False)
    return pd.to_numeric(s, errors="coerce").fillna(0).tolist()


def drop_dupes(rows, key):
    df = pd.DataFrame(rows)
    return df.drop_duplicates(subset=[key]).to_dict("records")
