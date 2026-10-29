#!/usr/bin/env python3
"""Build benchmark cases from third-party code (docs/REAL_CASES_PROTOCOL.md). Needs `gh` (logged in) and the pandas environments.
No model call.   .venv/bin/python scripts/build_real_case.py r1 r2
The function is copied verbatim with ast from the parent of the merge commit of the fixing pull request. The adapter, the inputs,
the known-good and the known-bad patches are ours. The upstream license is appended to docs/THIRD_PARTY_NOTICES.md."""
import ast, base64, json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT); sys.path.insert(0, str(ROOT))
from patchpilot import make_case

ALLOWED = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0"}
SPECS = {
 "r1": dict(
  name="r1_indsl_time_split", repo="cognitedata/indsl", pr=639, path="indsl/data_quality/outliers.py",
  func="_split_timeseries_into_time_and_value_arrays", imports="import numpy as np\nimport pandas as pd", fn="split_series",
  adapter='def split_series(index, values):\n    """Adapter (ours): ISO timestamps and floats in, plain lists out."""\n'
          '    x, y = _split_timeseries_into_time_and_value_arrays(pd.Series(values, index=pd.DatetimeIndex(index)))\n'
          '    return {"x": [round(float(v), 6) for v in x], "y": [float(v) for v in y]}\n',
  probes=[
   {"index": ["2024-01-01 00:00:00", "2024-01-01 00:00:10", "2024-01-01 00:00:25", "2024-01-01 00:01:00"], "values": [1.5, 2.5, 0.5, 3.0]},
   {"index": ["2023-06-30 23:59:50", "2023-07-01 00:00:05", "2023-07-01 12:30:00"], "values": [10.0, 20.0, 15.0]},
   {"index": ["2025-03-09 01:00:00", "2025-03-09 02:00:00", "2025-03-09 03:00:00", "2025-03-09 04:00:00", "2025-03-09 05:00:00"], "values": [0.1, 0.2, 0.3, 0.4, 0.5]},
   {"index": ["2022-12-31 23:00:00", "2023-01-01 01:30:00"], "values": [7.25, 8.75]}],
  good=('np.array(data.index, dtype=np.int64)', 'np.array(data.index.as_unit("ns"), dtype=np.int64)'),
  bad=("hardcode_microseconds", '(np.array(data.index, dtype=np.int64) - data.index[0].value) / 1e9',
       '(np.array(data.index, dtype=np.int64) - data.index[0].value // 1000) / 1e6',
       "assumes the new microsecond unit: right on the new library, wrong on the old one")),
 "r2": dict(
  name="r2_kythera_epoch_seconds", repo="ziagl888/Kythera", pr=229, path="tools/breadth_study.py",
  func="panel_to_compact", imports="import pandas as pd", fn="compact_records",
  adapter='def compact_records(open_time, close, volume, ema_50, ema_200):\n    """Adapter (ours): lists in (open_time as ISO strings), the compact dict out."""\n'
          '    df = pd.DataFrame({"open_time": pd.to_datetime(open_time), "close": close, "volume": volume, "ema_50": ema_50, "ema_200": ema_200})\n'
          '    return panel_to_compact(df)\n',
  probes=[
   {"open_time": ["2024-01-01 00:00:00", "2024-01-02 00:00:00", "2024-01-03 00:00:00"], "close": [42000.5, 42500.25, 41800.0],
    "volume": [1200.5, 980.25, 1500.0], "ema_50": [41000.1, 41100.2, 41200.3], "ema_200": [39000.5, 39010.5, 39020.5]},
   {"open_time": ["2024-06-15 08:00:00", "2024-06-15 12:00:00", "2024-06-15 16:00:00", "2024-06-15 20:00:00"], "close": [65000.0, 65250.5, 64800.75, 65100.0],
    "volume": [300.5, 410.25, 280.0, 350.75], "ema_50": [64000.5, 64050.5, 64100.5, 64150.5], "ema_200": [60000.25, 60010.25, 60020.25, 60030.25]},
   {"open_time": ["2023-12-31 00:00:00", "2024-01-01 00:00:00"], "close": [2300.5, 2350.25], "volume": [5000.0, 5200.5],
    "ema_50": [2200.1, 2210.2], "ema_200": [2000.5, 2001.5]}],
  good=('df["open_time"].astype("int64") // 10**9', 'df["open_time"].dt.as_unit("ns").astype("int64") // 10**9'),
  bad=("hardcode_microseconds", 'df["open_time"].astype("int64") // 10**9', 'df["open_time"].astype("int64") // 10**6',
       "assumes the new microsecond unit: right on the new library, wrong on the old one")),
}

def gh(*a):
    r = subprocess.run(["gh", *a], capture_output=True, text=True)
    if r.returncode: sys.exit(f"gh {' '.join(a)} failed: {r.stderr.strip()[:300]}")
    return r.stdout

def build(key):
    s = SPECS[key]; out = ROOT / "benchmarks" / s["name"]
    if out.exists(): sys.exit(f"{out} already exists")
    pr = json.loads(gh("pr", "view", str(s["pr"]), "--repo", s["repo"], "--json", "mergeCommit,url,state"))
    assert pr["state"] == "MERGED", pr
    merge = pr["mergeCommit"]["oid"]
    parent = gh("api", f"repos/{s['repo']}/commits/{merge}", "--jq", ".parents[0].sha").strip()
    src = gh("api", "-H", "Accept: application/vnd.github.raw", f"repos/{s['repo']}/contents/{s['path']}?ref={parent}")
    node = next(x for x in ast.parse(src).body if isinstance(x, ast.FunctionDef) and x.name == s["func"])
    seg = ast.get_source_segment(src, node)
    lic = json.loads(gh("api", f"repos/{s['repo']}/license?ref={parent}"))
    spdx = lic["license"]["spdx_id"]
    assert spdx in ALLOWED, f"license {spdx} is not allowed"
    header = (f'"""Third-party code. The function {s["func"]} is copied verbatim (by scripts/build_real_case.py, with ast) from\n'
              f'https://github.com/{s["repo"]}/blob/{parent}/{s["path"]}\n'
              f'(parent of merge commit {merge[:10]} of {pr["url"]}), license {spdx}. See docs/THIRD_PARTY_NOTICES.md.\n'
              f'Everything under the marker "adapter (ours)" was written for this project.\n"""\n{s["imports"]}\n\n\n')
    app = header + seg + "\n\n\n# --- adapter (ours) ---\n" + s["adapter"]
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "app.py").write_text(app); (Path(tmp) / "probes.json").write_text(json.dumps(s["probes"]))
        ref = json.loads((ROOT / "benchmarks/p7_censor_chained_iloc/case.json").read_text())
        argv = ["--src", f"{tmp}/app.py", "--fn", s["fn"], "--inputs", f"{tmp}/probes.json", "--old", os.path.join(ROOT, ref["old"]),
                "--new", os.path.join(ROOT, ref["new"]), "--lib", "pandas", "--out", str(out)]
        try:
            make_case.main(argv)
        except SystemExit as e:
            if e.code not in (0, None):
                print(f"{key}: NOT BUILT as a clean silent breakage (exit {e.code}); folder left for inspection if it exists:", out); return False
    (out / "case.json").write_text(json.dumps(ref) + "\n")
    for old, new in (s["good"],):
        assert old in app, "known-good anchor"
        (out / "known_good.json").write_text(json.dumps({"files": {"app.py": app.replace(old, new)}}, indent=1) + "\n")
    name, old, new, note = s["bad"]
    assert old in app, "known-bad anchor"
    (out / "known_bad").mkdir()
    (out / "known_bad" / f"{name}.json").write_text(json.dumps({"files": {"app.py": app.replace(old, new)}, "note": note}, indent=1) + "\n")
    notices = ROOT / "docs" / "THIRD_PARTY_NOTICES.md"; t = notices.read_text(); head = f"## {s['repo']} ({s['func']}), {spdx}"
    if head not in t:
        text = base64.b64decode(lic["content"]).decode()
        notices.write_text(t.rstrip("\n") + f"\n\n{head}\n\nUsed in `benchmarks/{s['name']}`. Source: https://github.com/{s['repo']}/blob/{parent}/{s['path']} "
                           f"(parent of merge commit {merge[:10]} of {pr['url']}). License file `{lic['path']}` at that commit:\n\n"
                           + "\n".join("    " + l for l in text.splitlines()) + "\n")
    print(f"{key}: built {out.name} from {s['repo']}@{parent[:10]} ({spdx})")
    return True

if __name__ == "__main__":
    ok = [build(k) for k in sys.argv[1:]]
    sys.exit(0 if all(ok) else 3)
