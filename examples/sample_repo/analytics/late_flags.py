"""Sample module (written for this project): flags the rows whose day is after a cutoff, with a chained assignment."""
import pandas as pd


def late_flags(days, cutoff):
    table = pd.DataFrame({"day": days})
    table["late"] = 0
    for position in range(len(table)):
        if table["day"].iloc[position] > cutoff:
            table["late"].iloc[position] = 1
    return table["late"].tolist()
