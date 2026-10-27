import numpy as np
import pandas as pd


def label_histogram(records):
    """Count (team, label) pairs. A label of "" means "not set"; null means "never provided".

    records: [[team, label], ...]. Returns [[team, label, count], ...] in the library's own order.
    """
    df = pd.DataFrame(records, columns=["team", "label"])
    df["label"] = df["label"].where(df["label"] != "", np.nan)
    df["label"] = df["label"].astype(str)
    counts = df.value_counts(sort=False)
    return [[team, label, int(n)] for (team, label), n in counts.items()]
