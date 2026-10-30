"""Sample module (written for this project): the product of the box dimensions, with an alias NumPy 2 removed."""
import numpy as np


def total_volume(dims):
    return int(np.product(dims))
