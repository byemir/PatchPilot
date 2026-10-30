import numpy as np


def range_text(values):
    a = np.array(values)
    return f"range: {[np.min(a), np.max(a)]}"


def running_balance(amounts):
    return np.round(np.cumsum(amounts), 2).tolist()


def add_bonus(score, bonus):
    return int(np.uint8(score) + bonus)


def nearest_percentile(values, q):
    return float(np.percentile(values, q, method="nearest"))


def zscores(values):
    a = np.array(values, dtype=float)
    return np.round((a - a.mean()) / a.std(), 3).tolist()


def bucket_counts(values, edges):
    return np.histogram(values, bins=edges)[0].tolist()


def mean_of_means(groups):
    return float(np.mean([np.mean(g) for g in groups]))


def round_half(values):
    return (np.round(np.array(values) * 2) / 2).tolist()
