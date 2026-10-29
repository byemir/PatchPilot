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
NP_OLD, NP_NEW = ".sandboxes/np126/bin/python", ".sandboxes/np2/bin/python"

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


Q1 = '''"""Own code (written for this project): clean a score column through variables that point into the frame."""
import pandas as pd


def clean_scores(ids, scores, floor, cap):
    frame = pd.DataFrame({"id": ids, "score": scores})
    low = frame["score"]
    low[low < floor] = floor
    high = frame["score"]
    high[high > cap] = cap
    return {"id": frame["id"].tolist(), "score": [round(float(x), 6) for x in frame["score"]]}
'''

Q2 = '''"""Own code (written for this project): epoch seconds for a list of timestamp strings, with gaps kept as None."""
import pandas as pd


def epoch_with_gaps(times):
    stamps = pd.to_datetime(times)
    seconds = stamps.astype("int64") // 10**9
    return [None if pd.isna(t) else int(s) for t, s in zip(stamps, seconds)]
'''

Q3 = '''"""Own code (written for this project): one report line per column with its largest value, as text."""
import numpy as np


def describe_columns(columns):
    lines = []
    for name in sorted(columns):
        values = np.array(columns[name])
        lines.append(f"{name}={values.max()!r}")
    return lines
'''

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
    "q1": dict(
        name="q1_score_aliases", src=Q1, fn="clean_scores",
        probes=[
            {"ids": [1, 2, 3, 4], "scores": [5.0, -2.0, 3.5, -0.5], "floor": 0.0, "cap": 10.0},
            {"ids": [7, 8, 9], "scores": [-1.0, 2.0, -3.0], "floor": 0.5, "cap": 9.0},
            {"ids": [10, 11, 12, 13], "scores": [4.0, -4.0, 1.0, -1.0], "floor": 1.0, "cap": 20.0}],
        hidden=[
            {"ids": [1, 2, 3], "scores": [5.0, 12.5, 3.0], "floor": 0.0, "cap": 10.0},
            {"ids": [4, 5, 6, 7], "scores": [-2.0, 15.0, 8.0, 30.0], "floor": 0.0, "cap": 10.0},
            {"ids": [8, 9], "scores": [100.0, -100.0], "floor": -5.0, "cap": 50.0},
            {"ids": [10, 11, 12], "scores": [1.0, 2.0, 3.0], "floor": 0.0, "cap": 10.0}],
        good=('    low = frame["score"]\n    low[low < floor] = floor\n    high = frame["score"]\n    high[high > cap] = cap\n',
              '    frame["score"] = frame["score"].clip(lower=floor, upper=cap)\n'),
        bad=[("floor_only", '    low = frame["score"]\n    low[low < floor] = floor\n', '    frame["score"] = frame["score"].clip(lower=floor)\n',
              "repairs the floor step only: right on the visible inputs (nothing exceeds the cap), wrong when a value is above the cap"),
             ("cap_only", '    high = frame["score"]\n    high[high > cap] = cap\n', '    frame["score"] = frame["score"].clip(upper=cap)\n',
              "repairs the cap step only: the floor step still does nothing on pandas 3")],
        lib="pandas", old=OLD, new=NEW),
    "q2": dict(
        name="q2_epoch_with_gaps", src=Q2, fn="epoch_with_gaps",
        probes=[
            {"times": ["2024-01-01 00:00:00", "2024-01-02 12:30:00", "2024-02-29 23:59:59"]},
            {"times": ["2023-06-30 23:59:50", None, "2023-07-01 00:00:05"]},
            {"times": ["2025-03-09 01:00:00", "2025-03-09 03:00:00"]}],
        hidden=[
            {"times": ["2024-03-10 01:00:00+02:00", "2024-03-10 03:00:00+02:00"]},
            {"times": ["2024-01-01 00:00:00.123456789", "2024-01-01 00:00:01.000000001"]},
            {"times": [None, "2024-05-05 05:05:05", None]},
            {"times": ["2024-12-31 23:59:59.999999", "2025-01-01 00:00:00.000000"]}],
        good=('    seconds = stamps.astype("int64") // 10**9\n', '    seconds = stamps.as_unit("ns").astype("int64") // 10**9\n'),
        bad=[("hardcode_microseconds", 'stamps.astype("int64") // 10**9', 'stamps.astype("int64") // 10**6',
              "assumes the new microsecond unit: right on the new library for plain strings, wrong on the old one"),
             ("branch_on_version", 'stamps.astype("int64") // 10**9',
              'stamps.astype("int64") // (10**6 if int(pd.__version__.split(".")[0]) >= 3 else 10**9)',
              "divides by 10**6 on pandas 3: right for microsecond data, wrong for nanosecond input"),
             ("subtract_epoch", '    seconds = stamps.astype("int64") // 10**9\n', '    seconds = (stamps - pd.Timestamp("1970-01-01")).total_seconds()\n',
              "unit independent for plain strings, raises for timestamps with a UTC offset")],
        lib="pandas", old=OLD, new=NEW),
    "q3": dict(
        name="q3_scalar_repr", src=Q3, fn="describe_columns",
        probes=[
            {"columns": {"price": [1.5, 2.0, 3.25], "rate": [0.5, 0.25]}},
            {"columns": {"load": [0.75, 0.5, 0.125], "temp": [20.5, 21.0]}},
            {"columns": {"x": [2.5, 1.25], "y": [9.75]}}],
        hidden=[
            {"columns": {"count": [1, 2, 3], "total": [10, 20]}},
            {"columns": {"on": [True, False], "ok": [True, True]}},
            {"columns": {"a": [1, 2], "b": [0.5, 1.5], "c": [False, True]}},
            {"columns": {"big": [100000000000000000000.0, 1.0], "small": [1e-07, 2e-07]}}],
        good=('{values.max()!r}', '{values.max().item()!r}'),
        bad=[("float_cast", '{values.max()!r}', '{float(values.max())!r}',
              "right for float columns, wrong for integer and boolean columns (3 becomes 3.0)")],
        lib="numpy", old=NP_OLD, new=NP_NEW),
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
        lib, old_py, new_py = s.get("lib", "pandas"), s.get("old", OLD), s.get("new", NEW)
        argv = ["--src", f"{tmp}/app.py", "--fn", s["fn"], "--inputs", f"{tmp}/probes.json", "--old", str(ROOT / old_py),
                "--new", str(ROOT / new_py), "--lib", lib, "--out", str(out)]
        if s.get("hidden"):
            (Path(tmp) / "hidden.json").write_text(json.dumps(s["hidden"]))
            argv += ["--hidden-inputs", f"{tmp}/hidden.json"]
        try:
            make_case.main(argv)
        except SystemExit as e:
            if e.code not in (0, None):
                print(f"{key}: NOT BUILT (exit {e.code})")
                return False
    (out / "case.json").write_text(json.dumps({"lib": lib, "old": old_py, "new": new_py, "gen": 2}) + "\n")
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
