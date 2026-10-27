import pandas as pd


def category_report(rows, categories):
    """Per-category totals and the number of columns each group carries.

    rows: [[category, amount], ...]; categories: every known category, in report order.
    """
    df = pd.DataFrame(rows, columns=["cat", "amount"])
    df["cat"] = pd.Categorical(df["cat"], categories=categories)
    grouped = df.groupby("cat")
    totals = grouped["amount"].sum()
    counts = grouped.size()
    widths = grouped.apply(lambda part: part.shape[1])
    return [[str(c), int(totals[c]), int(counts[c]), int(widths.get(c, -1))] for c in totals.index]
