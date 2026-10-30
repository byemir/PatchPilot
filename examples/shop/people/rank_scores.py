"""Shop module (written for this project): dense rank of loyalty scores, best score first."""
import pandas as pd

def rank_scores(scores):
    return pd.Series(scores).rank(method="dense", ascending=False).astype(int).tolist()
