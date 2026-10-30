"""Shop module (written for this project): price after a discount, from a float32 price column."""
import numpy as np

def discounted_price(price, rate):
    p = np.float32(price)
    return float(p * (1.0 - rate))
