"""Shop module (written for this project): how many orders fall into each price band."""
import pandas as pd

def size_buckets(amounts):
    bands = pd.cut(pd.Series(amounts), bins=[0, 20, 50, 100, 1000], labels=["low", "mid", "high", "vip"])
    return {str(k): int(v) for k, v in bands.value_counts().sort_index().items()}
