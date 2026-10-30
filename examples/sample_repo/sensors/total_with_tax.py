"""Sample module (written for this project): the sum of prices with a tax rate applied to each price."""
import numpy as np


def total_with_tax(prices, rate):
    total = 0.0
    for p in prices:
        total += float(np.float32(p) * (1.0 + rate))
    return round(total, 9)
