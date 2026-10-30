"""Sample module (written for this project): how many orders fall into each size class, including the empty classes."""
import pandas as pd

CLASSES = ["small", "medium", "large", "huge"]


def counts_by_size(sizes):
    table = pd.DataFrame({"size": pd.Categorical(sizes, categories=CLASSES)})
    counted = table.groupby("size").size()
    return {str(k): int(v) for k, v in counted.items()}
