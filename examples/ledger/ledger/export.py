import pandas as pd


def to_csv_lines(rows):
    return pd.DataFrame(rows).to_csv(index=False).splitlines()


def category_share(rows):
    df = pd.DataFrame(rows)
    return df["category"].value_counts(normalize=True).round(2).to_dict()


def spend_table(rows):
    df = pd.DataFrame(rows)
    t = df.pivot_table(index="who", columns="category", values="amount", aggfunc="sum", fill_value=0)
    return t.to_dict()


def biggest_per_person(rows):
    df = pd.DataFrame(rows)
    return df.groupby("who").apply(lambda g: g["amount"].max()).to_dict()


def label_rows(rows):
    df = pd.DataFrame(rows)
    df["label"] = df["who"].str.upper() + ":" + df["category"].astype(str)
    return df["label"].tolist()
