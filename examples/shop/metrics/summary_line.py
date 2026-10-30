"""Shop module (written for this project): one log line with the maximum and the values."""
import numpy as np

def summary_line(values):
    a = np.asarray(values, dtype=np.float64)
    return "max=" + str(np.max(a)) + " values=" + str(list(a))
