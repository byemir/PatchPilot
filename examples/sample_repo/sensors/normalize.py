"""Sample module (written for this project): scale values to zero mean and unit variance. Same on NumPy 1.26 and 2.x."""
import numpy as np


def normalize(values):
    arr = np.asarray(values, dtype=np.float64)
    return [round(float(x), 9) for x in (arr - arr.mean()) / arr.std()]
