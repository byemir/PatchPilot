"""Example function for `patchpilot.repair` (written for this project). It marks a share of subjects as dropped out,
with a seeded random choice, and writes the flags with a chained assignment. That works on pandas 2.3 and does
nothing on pandas 3.0 (copy-on-write): the flags stay 1 and no error is raised."""
import random

import pandas as pd


def mark_dropouts(n_subjects, dropout_rate, seed):
    table = pd.DataFrame({"subject": list(range(n_subjects)), "observed": [1] * n_subjects})
    rng = random.Random(seed)
    n_drop = int(round(n_subjects * dropout_rate))
    for position in rng.sample(range(n_subjects), n_drop):
        table["observed"].iloc[position] = 0
    return {"subjects": table["subject"].tolist(), "observed": table["observed"].tolist()}
