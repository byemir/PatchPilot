"""Shop module (written for this project): rounded score per team as text for a report."""
import numpy as np

def scores_text(teams, raw):
    rounded = np.round(np.asarray(raw, dtype=np.float64), 1)
    return str(dict(zip(teams, rounded)))
