"""Offline check of make_case on three existing benchmark functions (no model call).

    python -m patchpilot.make_case_test
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

PD = (".sandboxes/pd23/bin/python", ".sandboxes/pd30/bin/python")
NP = (".sandboxes/np126/bin/python", ".sandboxes/np2/bin/python")
CASES = [
    ("benchmarks/p5_chained_assignment", "apply_discounts", "pandas", PD),
    ("benchmarks/p7_censor_chained_iloc", "censor_records", "pandas", PD),
    ("benchmarks/n8_string_to_bool", "enabled_devices", "numpy", NP),
]

passed = 0
with tempfile.TemporaryDirectory() as tmp:
    for d, fn, lib, (old, new) in CASES:
        out = Path(tmp) / Path(d).name
        r = subprocess.run([sys.executable, "-m", "patchpilot.make_case", "--src", f"{d}/app.py", "--fn", fn,
                            "--inputs", f"{d}/inputs.json", "--old", old, "--new", new, "--lib", lib, "--out", str(out)],
                           capture_output=True, text=True)
        assert r.returncode == 0, f"{d}: make_case failed: {r.stderr[-400:]}"
        for name in ("app.py", "run_case.py", "case.json", "golden.json", "hidden_inputs.json", "hidden_golden.json"):
            assert (out / name).exists(), f"{d}: {name} missing"
        assert "hidden old=OK" in r.stdout and "new=SILENT_BREAKAGE" in r.stdout, r.stdout
        passed += 1
        print(f"ok  {d}")
    r = subprocess.run([sys.executable, "-m", "patchpilot.make_case", "--src", "benchmarks/n8_string_to_bool/app.py",
                        "--fn", "no_such_function", "--inputs", "benchmarks/n8_string_to_bool/inputs.json",
                        "--old", NP[0], "--new", NP[1], "--lib", "numpy", "--out", str(Path(tmp) / "x")],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "no top-level function" in r.stderr and not (Path(tmp) / "x").exists()
    passed += 1
    print("ok  unknown function is refused")
print(f"make_case_test: {passed} checks passed")
