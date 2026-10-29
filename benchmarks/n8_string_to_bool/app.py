import numpy as np


def enabled_devices(flags):
    """Which devices are enabled.

    flags: strings read from a text file, "0" for off and any other number for on.
    """
    arr = np.array(flags)
    enabled = arr.astype(bool)
    return {"count": int(enabled.sum()), "enabled": [bool(x) for x in enabled]}
