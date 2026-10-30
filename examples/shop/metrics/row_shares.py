"""Shop module (written for this project): each row's share of its total."""
import numpy as np

def row_shares(matrix):
    m = np.asarray(matrix, dtype=np.float64)
    return np.round(m / m.sum(axis=1, keepdims=True), 4).tolist()
