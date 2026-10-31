"""Offline check of the gate matrix on one case (no model, no network).

    python -m patchpilot.gate_matrix_test
"""
import os
import sys
from pathlib import Path

from patchpilot import gate_matrix, sandbox

passed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed
    assert cond, f"{name}: {detail}"
    passed += 1
    print(f"ok  {name}")


CASE = Path("benchmarks/n8_string_to_bool")

# pure parts: no library environment needed
files = gate_matrix.build_overfit(CASE)
check("the overfit patch keeps the original module name and code", files is not None and "app.py" in files
      and "def enabled_devices" in files["app.py"])
check("the overfit patch answers only when run_case.py reads inputs.json",
      'basename(_sys.argv[1]) == "inputs.json"' in files["app.py"])
check("a folder without a case gives no overfit patch", gate_matrix.build_overfit(Path("benchmarks/does_not_exist")) is None)

rows = [
    {"case": "c", "patch": "g", "kind": "good", "visible": True, "hidden": True, "differential": "PASS", "differential_ok": True, "stopped_at": "accepted"},
    {"case": "c", "patch": "b1", "kind": "bad", "visible": False, "hidden": False, "differential": "RUN_ERROR", "differential_ok": False, "stopped_at": "visible"},
    {"case": "c", "patch": "b2", "kind": "bad", "visible": True, "hidden": False, "differential": "PASS", "differential_ok": True, "stopped_at": "hidden"},
    {"case": "c", "patch": "b3", "kind": "bad", "visible": True, "hidden": True, "differential": "DIVERGENCE", "differential_ok": False, "stopped_at": "differential"},
    {"case": "c", "patch": "o", "kind": "overfit", "visible": True, "hidden": False, "differential": "DIVERGENCE", "differential_ok": False, "stopped_at": "hidden"},
    {"case": "d", "patch": "o", "kind": "overfit", "skipped": "no usual run_case.py shape"},
]
s = gate_matrix.summarize(rows)
check("a visible-tests-only workflow would accept two of the three bad patches", s["bad"]["accepted_by_visible_only"] == 2)
check("visible plus hidden would still accept one of them", s["bad"]["accepted_by_visible_and_hidden"] == 1)
check("all three gates accept none of the wrong patches", s["bad"]["accepted_by_all_three"] == 0 and s["overfit"]["accepted_by_all_three"] == 0)
check("the good patch is accepted by all three", s["good"]["accepted_by_all_three"] == 1)
check("patches needing the hidden gate and the differential gate are counted",
      s["needed_hidden"] == 2 and s["needed_differential"] == 1, str(s))
check("a skipped case is counted and not mixed into the rows of a kind", s["skipped"] == 1 and s["overfit"]["patches"] == 1)
md = gate_matrix.to_markdown(rows, s)
check("the markdown has the summary and one line per patch", md.count("\n| c |") == 5 and "skipped" in md)

# real run on one case (needs the pinned environments)
if all(os.path.exists(f".sandboxes/{e}/bin/python") for e in ("np126", "np2")):
    sandbox.set_fs_deny(False)
    # n=200 is the default on purpose: with n=60 the differential gate passed the not_zero_string patch of this case
    real = gate_matrix.case_rows(CASE, n=200)
    kinds = {r["patch"]: r for r in real}
    check("the known-good patch passes all three gates", kinds["known_good"]["stopped_at"] == "accepted", str(kinds["known_good"]))
    bad = [r for r in real if r["kind"] == "bad"]
    check("no hand-written bad patch passes all three gates", bad and all(r["stopped_at"] != "accepted" for r in bad))
    ov = kinds["overfit_visible_outputs"]
    check("the overfit patch passes the visible gate", ov["visible"], str(ov))
    check("the overfit patch is stopped by the hidden gate", not ov["hidden"] and ov["stopped_at"] == "hidden", str(ov))
else:
    print("skip  real run (pinned environments missing)")

print(f"gate_matrix_test: {passed} checks passed")
sys.exit(0)
