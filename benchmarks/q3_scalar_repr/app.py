"""Own code (written for this project): one report line per column with its largest value, as text."""
import numpy as np


def describe_columns(columns):
    lines = []
    for name in sorted(columns):
        values = np.array(columns[name])
        lines.append(f"{name}={values.max()!r}")
    return lines
