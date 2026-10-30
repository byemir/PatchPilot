"""Shop module (written for this project): area under a sampled curve."""
import numpy as np

def area_under(xs, ys):
    return float(np.trapz(ys, xs))
