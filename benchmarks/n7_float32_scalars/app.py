import numpy as np


def weighted_score(values, rate, bonus):
    """Total of values * rate (float32 samples) and how many weighted values exceed `bonus`."""
    samples = np.asarray(values, dtype=np.float32)
    total = np.float32(0)
    hits = 0
    for v in samples:
        x = v * rate
        total += x
        if x > bonus:
            hits += 1
    return [round(float(total), 9), hits]
