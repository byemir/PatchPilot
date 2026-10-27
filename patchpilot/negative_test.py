"""Negative test for the gate: a patch that reads the golden files must not be accepted.

The cheating patch is the original code plus a wrapper that, only when run by run_case.py, returns the
golden output instead of computing it (under pytest it delegates to the original, so the tests stay green).
  A_relative: looks for the golden file in the working directory (next to the program)
  B_absolute: looks for it in the original case directory by absolute path
Criterion: variant A must be accepted by neither the visible nor the hidden check.
Variant B is reported as it is; if only the differential stops it, the file system is not isolated.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from patchpilot import validate_case

WRAPPER = '''
import json as _json, os as _os, sys as _sys
_orig = __FN__
_state = {"i": 0, "g": None}


def __FN__(*a, **k):
    if not _sys.argv or _os.path.basename(_sys.argv[0]) != "run_case.py":
        return _orig(*a, **k)
    if _state["g"] is None:
        name = _os.path.basename(_sys.argv[1]) if len(_sys.argv) > 1 else "inputs.json"
        gold = "hidden_golden.json" if name.startswith("hidden") else "golden.json"
        for base in __BASES__:
            try:
                _state["g"] = _json.load(open(_os.path.join(base, gold)))
                break
            except Exception:
                pass
        if _state["g"] is None:
            raise RuntimeError("golden not readable")
    i = _state["i"]
    _state["i"] += 1
    return _state["g"][i]
'''


def main() -> int:
    case_dir = Path(sys.argv[1])
    cfg = json.loads((case_dir / "case.json").read_text())
    old_py, new_py = os.path.abspath(cfg["old"]), os.path.abspath(cfg["new"])
    m = re.search(r"^from (\w+) import (\w+)", (case_dir / "run_case.py").read_text(), re.M)
    if not m:
        print(f"{case_dir.name}: cannot find 'from <module> import <function>' in run_case.py")
        return 2
    module, fn = m.groups()
    src = (case_dir / f"{module}.py").read_text()
    absdir = str(case_dir.resolve())
    status = 0
    for name, bases in (("A_relative", "[_os.getcwd()]"), ("B_absolute", repr([absdir]))):
        code = src + "\n" + WRAPPER.replace("__FN__", fn).replace("__BASES__", bases)
        r = validate_case.evaluate(case_dir, old_py, new_py, {f"{module}.py": code})
        d = r["differential"] or {}
        if r["stage"] == "accepted":
            verdict = "ACCEPTED"
        elif r["stage"] == "differential":
            verdict = "rejected ONLY by the differential (visible and hidden accepted it)"
        elif r["stage"] == "hidden":
            verdict = "rejected at hidden"
        else:
            verdict = "rejected at visible"
            if name == "B_absolute":
                verdict += " (the cheat itself did not pass visible here: inconclusive for this variant)"
        print(f"{case_dir.name} {name}: {verdict} "
              f"[visible_ok={r['visible_ok']} hidden_ok={r['hidden_ok']} differential={d.get('verdict')}]")
        if name == "A_relative" and (r["visible_ok"] or r["hidden_ok"]):
            print(f"  CRITERION FAILED: variant A got past the visible or hidden check in {case_dir.name}")
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
