"""Shop module (written for this project): the 90th percentile latency, rounded down to an observed value."""
import numpy as np

def p90_latency(ms):
    return float(np.percentile(np.asarray(ms, dtype=np.float64), 90, interpolation="lower"))
