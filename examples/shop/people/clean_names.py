"""Shop module (written for this project): trims and title-cases customer names."""
import pandas as pd

def clean_names(names):
    s = pd.Series(names)
    if s.dtype == object:
        s = s.str.strip().str.title()
    return s.tolist()
