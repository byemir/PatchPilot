"""Own code (written for this project): clean a score column through variables that point into the frame."""
import pandas as pd


def clean_scores(ids, scores, floor, cap):
    frame = pd.DataFrame({"id": ids, "score": scores})
    low = frame["score"]
    low[low < floor] = floor
    high = frame["score"]
    high[high > cap] = cap
    return {"id": frame["id"].tolist(), "score": [round(float(x), 6) for x in frame["score"]]}
