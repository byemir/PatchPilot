"""Shop module (written for this project): the n customers with the most orders."""
import pandas as pd

def top_customers(names, n):
    counts = pd.Series(names).value_counts().head(n)
    return [[str(k), int(v)] for k, v in counts.items()]
