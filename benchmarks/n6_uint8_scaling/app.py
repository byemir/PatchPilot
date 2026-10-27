import numpy as np


def total_brightness(pixels, gain):
    """Sum of pixel values scaled by an integer gain."""
    arr = np.asarray(pixels, dtype=np.uint8)
    total = 0
    for p in arr:
        total += p * gain
    return int(total)
