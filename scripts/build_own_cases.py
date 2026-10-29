#!/usr/bin/env python3
"""Build the three benchmark cases whose code we wrote ourselves (no model call, no network).
    .venv/bin/python scripts/build_own_cases.py o1 o2 o3
Each case is one self-contained function in app.py plus inputs; golden files and held-out inputs come from the old
interpreter through patchpilot.make_case. The known-good and known-bad patches are text replacements in app.py."""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
from patchpilot import make_case  # noqa: E402

OLD, NEW = ".sandboxes/pd23/bin/python", ".sandboxes/pd30/bin/python"

O1 = '''"""Own code (written for this project): elapsed time of a sampled signal."""
import numpy as np
import pandas as pd


def elapsed_seconds(timestamps, values):
    """Seconds since the first sample for every sample, together with the values as floats."""
    index = pd.DatetimeIndex(pd.to_datetime(timestamps))
    ticks = np.array(index, dtype=np.int64)
    seconds = (ticks - ticks[0]) / 1e9
    return {"seconds": [round(float(s), 6) for s in seconds], "values": [float(v) for v in values]}
'''

O2 = '''"""Own code (written for this project): price bars as compact arrays with epoch seconds."""
import pandas as pd


def bars_to_epoch(times, close, volume):
    """Bars given as parallel lists (times as ISO strings) -> JSON-safe arrays with epoch seconds."""
    frame = pd.DataFrame({"t": pd.to_datetime(times), "c": close, "v": volume})
    return {
        "t": (frame["t"].astype("int64") // 10**9).tolist(),
        "c": [float(x) for x in frame["c"]],
        "v": [float(x) for x in frame["v"]],
    }
'''

O3 = Path("examples/own_function/subject_dropout.py").read_text()

SPECS = {
    "o1": dict(
        name="o1_elapsed_seconds", src=O1, fn="elapsed_seconds",
        probes=[
            {"timestamps": ["2024-01-01 00:00:00", "2024-01-01 00:00:10", "2024-01-01 00:00:25", "2024-01-01 00:01:00"], "values": [1.5, 2.5, 0.5, 3.0]},
            {"timestamps": ["2023-06-30 23:59:50", "2023-07-01 00:00:05", "2023-07-01 12:30:00"], "values": [10.0, 20.0, 15.0]},
            {"timestamps": ["2025-03-09 01:00:00", "2025-03-09 02:00:00", "2025-03-09 03:00:00", "2025-03-09 04:00:00"], "values": [0.1, 0.2, 0.3, 0.4]},
            {"timestamps": ["2022-12-31 23:00:00", "2023-01-01 01:30:00"], "values": [7.25, 8.75]}],
        good=("np.array(index, dtype=np.int64)", 'np.array(index.as_unit("ns"), dtype=np.int64)'),
        bad=[("hardcode_microseconds", "(ticks - ticks[0]) / 1e9", "(ticks - ticks[0]) / 1e6",
              "assumes the new microsecond unit: right on the new library, wrong on the old one")]),
    "o2": dict(
        name="o2_bars_epoch_seconds", src=O2, fn="bars_to_epoch",
        probes=[
            {"times": ["2024-01-01 00:00:00", "2024-01-02 00:00:00", "2024-01-03 00:00:00"], "close": [42000.5, 42500.25, 41800.0], "volume": [1200.5, 980.25, 1500.0]},
            {"times": ["2024-06-15 08:00:00", "2024-06-15 12:00:00", "2024-06-15 16:00:00", "2024-06-15 20:00:00"], "close": [65000.0, 65250.5, 64800.75, 65100.0], "volume": [300.5, 410.25, 280.0, 350.75]},
            {"times": ["2023-12-31 00:00:00", "2024-01-01 00:00:00"], "close": [2300.5, 2350.25], "volume": [5000.0, 5200.5]}],
        good=('frame["t"].astype("int64") // 10**9', 'frame["t"].dt.as_unit("ns").astype("int64") // 10**9'),
        bad=[("hardcode_microseconds", 'frame["t"].astype("int64") // 10**9', 'frame["t"].astype("int64") // 10**6',
              "assumes the new microsecond unit: right on the new library, wrong on the old one"),
             ("branch_on_version", 'frame["t"].astype("int64") // 10**9',
              'frame["t"].astype("int64") // (10**6 if int(pd.__version__.split(".")[0]) >= 3 else 10**9)',
              "divides by 10**6 on pandas 3: right for microsecond data, wrong for nanosecond input (a constructed example of a patch that "
              "passes inputs built from plain strings)")]),
    "o3": dict(
        name="o3_subject_dropout", src=O3, fn="mark_dropouts",
        probes=json.loads(Path("examples/own_function/probes.json").read_text()),
        good=('table["observed"].iloc[position] = 0', 'table.iloc[position, table.columns.get_loc("observed")] = 0'),
        bad=[("chained_row", 'table["observed"].iloc[position] = 0', 'table.iloc[position]["observed"] = 0',
              "still a chained assignment: nothing is written on pandas 3"),
             ("first_rows_only", 'for position in rng.sample(range(n_subjects), n_drop):\n        table["observed"].iloc[position] = 0',
              'rng.sample(range(n_subjects), n_drop)\n    table.loc[: n_drop - 1, "observed"] = 0',
              "writes on both libraries but marks the first rows instead of the sampled ones")]),
}


def build(key):
    s = SPECS[key]
    out = ROOT / "benchmarks" / s["name"]
    if out.exists():
        sys.exit(f"{out} already exists")
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "app.py").write_text(s["src"])
        (Path(tmp) / "probes.json").write_text(json.dumps(s["probes"]))
        argv = ["--src", f"{tmp}/app.py", "--fn", s["fn"], "--inputs", f"{tmp}/probes.json", "--old", str(ROOT / OLD),
                "--new", str(ROOT / NEW), "--lib", "pandas", "--out", str(out)]
        try:
            make_case.main(argv)
        except SystemExit as e:
            if e.code not in (0, None):
                print(f"{key}: NOT BUILT (exit {e.code})")
                return False
    (out / "case.json").write_text(json.dumps({"lib": "pandas", "old": OLD, "new": NEW, "gen": 2}) + "\n")
    old, new = s["good"]
    assert s["src"].count(old) == 1, ("known-good anchor", key)
    (out / "known_good.json").write_text(json.dumps({"files": {"app.py": s["src"].replace(old, new)}}, indent=1) + "\n")
    (out / "known_bad").mkdir(exist_ok=True)
    for name, o, n, note in s["bad"]:
        assert s["src"].count(o) == 1, ("known-bad anchor", key, name)
        (out / "known_bad" / f"{name}.json").write_text(json.dumps({"files": {"app.py": s["src"].replace(o, n)}, "note": note}, indent=1) + "\n")
    shutil.rmtree(out / "__pycache__", ignore_errors=True)
    print(f"{key}: built {out.name}")
    return True


if __name__ == "__main__":
    ok = [build(k) for k in sys.argv[1:]]
    sys.exit(0 if all(ok) else 3)
