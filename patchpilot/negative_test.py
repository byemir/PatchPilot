"""Negative tests for the gate and the OS isolation layer.

Cheat patches: the original code plus a wrapper that, only when run by run_case.py, returns the golden output
instead of computing it (under pytest it delegates to the original, so the tests stay green).
  A_relative: looks for the golden file in the working directory
  B_absolute: looks for it in the original case directory by absolute path
Criteria (OS layer on): neither variant passes the visible or the hidden check and the cheat reports that the
golden file could not be read. With --no-fs-deny the criterion for B is not applied (B is expected to succeed
there); that mode only documents what the unisolated gate lets through.

  python -m patchpilot.negative_test benchmarks/<case> [--no-fs-deny]
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from patchpilot import check, sandbox, validate_case

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


def run_variants(case_dir: Path, fs_deny: bool) -> int:
    cfg = json.loads((case_dir / "case.json").read_text())
    old_py, new_py = os.path.abspath(cfg["old"]), os.path.abspath(cfg["new"])
    m = re.search(r"^from (\w+) import (\w+)", (case_dir / "run_case.py").read_text(), re.M)
    if not m:
        print(f"{case_dir.name}: cannot find 'from <module> import <function>' in run_case.py")
        return 2
    module, fn = m.groups()
    src = (case_dir / f"{module}.py").read_text()
    status = 0
    for name, bases in (("A_relative", "[_os.getcwd()]"), ("B_absolute", repr([str(case_dir.resolve())]))):
        code = src + "\n" + WRAPPER.replace("__FN__", fn).replace("__BASES__", bases)
        files = {f"{module}.py": code}
        r = validate_case.evaluate(case_dir, old_py, new_py, files)
        probe = check.check(case_dir, new_py, files=files)
        act = probe["actual"]
        denied = isinstance(act, list) and bool(act) and all(
            isinstance(x, dict) and x.get("error") == "RuntimeError" for x in act)
        d = r["differential"] or {}
        print(f"{case_dir.name} {name}: stage={r['stage']} visible_ok={r['visible_ok']} hidden_ok={r['hidden_ok']} "
              f"differential={d.get('verdict')} golden_read_denied={denied} fs_deny={sandbox.FS_DENY}")
        must_block = name == "A_relative" or fs_deny
        if must_block and (r["visible_ok"] or r["hidden_ok"] or not denied):
            print(f"  CRITERION FAILED for {name}")
            status = 1
    return status


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("usage: python -m patchpilot.negative_test benchmarks/<case> [--no-fs-deny]")
    case_dir = Path(args[0])
    sandbox.ensure_clean_env()
    fs_deny = "--no-fs-deny" not in sys.argv
    sandbox.set_fs_deny(fs_deny)
    return run_variants(case_dir, fs_deny)


if __name__ == "__main__":
    sys.exit(main())
