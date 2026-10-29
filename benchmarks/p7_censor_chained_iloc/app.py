# `censor` and the imports above it are copied verbatim from scikit-FIBERS
# (https://github.com/UrbsLab/scikit-FIBERS), src/skfibers/simulators/SIM1.py at commit 356c6d5
# (the parent of the commit that fixed the chained assignment, issue #19). MIT License,
# Copyright (c) 2023 Ryan Urbanowicz. `censor_records` is a thin wrapper added for this benchmark.
import random
import copy
import numpy as np
import pandas as pd
pd.options.mode.chained_assignment = None  # default='warn'


def censor(df, censoring_frequency, random_seed=None):  
    df['Censoring'] = 1
    inst_to_censor = int(censoring_frequency * len(df))
    max_duration = max(df['Duration'])
    df = df.sample(frac=1, random_state=random_seed).reset_index(drop=True) #randomly shuffled
    censor_count = 0
    count = 0
    while censor_count < inst_to_censor:
        if random_seed:
            np.random.seed(random_seed + count)
        for index in range(len(df)):
            prob = df['Duration'].iloc[index] / max_duration
            choice = np.random.choice([0, 1], 1, p=[prob, 1 - prob])
            if censor_count >= inst_to_censor:
                break
            if choice == 0:
                censor_count += 1
            df['Censoring'].iloc[index] = choice
            count += 1
    return df


def censor_records(records, censoring_frequency, seed):
    """Run `censor` on rows of {"id", "Duration"} and return [[id, Duration, Censoring], ...] in the shuffled order.

    The seed is mapped to 1..1000 so that the run is always seeded (`censor` does not seed when the seed is 0 or None).
    """
    df = pd.DataFrame(records, columns=["id", "Duration"])
    out = censor(df, censoring_frequency, random_seed=int(seed) % 1000 + 1)
    return [[int(r.id), float(r.Duration), int(r.Censoring)] for r in out.itertuples()]
