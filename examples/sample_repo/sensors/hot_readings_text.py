"""Sample module (written for this project): the readings above a threshold, as text for a log line."""
import numpy as np


def hot_readings_text(values, threshold):
    arr = np.asarray(values, dtype=np.float64)
    return "hot: " + str(list(arr[arr > threshold]))
