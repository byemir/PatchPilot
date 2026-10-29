import numpy as np


def fleet_report(devices, gain):
    """Report on devices.

    devices: [{"flag": text read from a file ("0" off, any other number on), "level": 0..255}, ...]. gain: float.
    Returns, per device, [enabled, level + 100, level * gain rounded to 6 decimals], the total of level * gain
    rounded to 6 decimals, and the number of enabled devices.
    """
    rows = []
    total = np.float32(0)
    for d in devices:
        on = bool(np.array([d["flag"]]).astype(bool)[0])
        boosted = int(np.uint8(d["level"]) + 100)
        scaled = np.float32(d["level"]) * gain
        total = total + scaled
        rows.append([on, boosted, round(float(scaled), 6)])
    return {"rows": rows, "total": round(float(total), 6), "enabled": sum(r[0] for r in rows)}
