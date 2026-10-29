import random
import copy
import numpy as np
import pandas as pd


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


def censor_records(records, censoring_frequency, random_seed):
    """Adapter: list of {"Duration": ...} rows in, list of rows out (censor itself is unchanged upstream code)."""
    out = censor(pd.DataFrame(records), censoring_frequency, random_seed)
    return [{"Duration": int(r["Duration"]), "Censoring": int(r["Censoring"])} for r in out.to_dict("records")]
