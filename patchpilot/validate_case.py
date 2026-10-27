"""Validate a benchmark case by running it (a case that fails any gate is not counted).

Gates:
  1. visible: OLD library -> OK, NEW library -> SILENT_BREAKAGE, tests green on both
  2. hidden : OLD -> OK, NEW -> SILENT_BREAKAGE (the held-out inputs must expose the breakage too)
  3. known_good.json is accepted by the full pipeline (visible + hidden + generated-input differential)
  4. every known_bad/*.json is rejected; the stage that rejects it is recorded, and
     `naive_passes_visible` says whether at least one bad patch gets past the visible check
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from patchpilot import check, differential, sandbox


def evaluate(case_dir: Path, old_py: str, new_py: str, files: dict, n: int = 200) -> dict:
    vo, vn = check.check(case_dir, old_py, files=files), check.check(case_dir, new_py, files=files)
    ho = check.check(case_dir, old_py, "hidden_inputs.json", "hidden_golden.json", files=files)
    hn = check.check(case_dir, new_py, "hidden_inputs.json", "hidden_golden.json", files=files)
    visible = vo["verdict"] == "OK" and vn["verdict"] == "OK"
    hidden = ho["verdict"] == "OK" and hn["verdict"] == "OK"
    diff = differential.differential(case_dir, old_py, new_py, files, n=n) if visible and hidden else None
    if not visible:
        stage = "visible"
    elif not hidden:
        stage = "hidden"
    elif diff["verdict"] in ("DIVERGENCE", "RUN_ERROR"):
        stage = "differential"
    else:
        stage = "accepted"
    return {"stage": stage, "visible_ok": visible, "hidden_ok": hidden,
            "differential": diff and {k: diff.get(k) for k in ("verdict", "valid", "core_divergences", "reason")}}


def validate(case_dir) -> dict:
    case_dir = Path(case_dir)
    cfg = json.loads((case_dir / "case.json").read_text())
    old_py, new_py = os.path.abspath(cfg["old"]), os.path.abspath(cfg["new"])
    vo, vn = check.check(case_dir, old_py), check.check(case_dir, new_py)
    ho = check.check(case_dir, old_py, "hidden_inputs.json", "hidden_golden.json")
    hn = check.check(case_dir, new_py, "hidden_inputs.json", "hidden_golden.json")
    gates = {
        "old_ok": vo["verdict"] == "OK",
        "new_silent_breakage": vn["verdict"] == "SILENT_BREAKAGE",
        "tests_green_both": vo["tests_pass"] and vn["tests_pass"],
        "hidden_old_ok": ho["verdict"] == "OK",
        "hidden_new_breaks": hn["verdict"] == "SILENT_BREAKAGE",
    }
    good_path = case_dir / "known_good.json"
    good = evaluate(case_dir, old_py, new_py, json.loads(good_path.read_text())["files"]) if good_path.exists() else None
    gates["known_good_accepted"] = bool(good and good["stage"] == "accepted")
    bad = {}
    for p in sorted((case_dir / "known_bad").glob("*.json")):
        bad[p.stem] = evaluate(case_dir, old_py, new_py, json.loads(p.read_text())["files"])
    gates["has_known_bad"] = bool(bad)
    gates["all_known_bad_rejected"] = bool(bad) and all(b["stage"] != "accepted" for b in bad.values())
    return {"case": case_dir.name, "valid": all(gates.values()), "gates": gates,
            "naive_passes_visible": any(b["stage"] != "visible" for b in bad.values()),
            "known_good": good, "known_bad": bad,
            "old_version_output": vo["actual"], "new_version_output": vn["actual"]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="+")
    ap.add_argument("--out", help="also write the full JSON report here")
    ap.add_argument("--fs-deny", action="store_true",
                    help="also run the fixtures under the OS file-system isolation (default: off, fixtures are trusted)")
    a = ap.parse_args()
    sandbox.set_fs_deny(a.fs_deny)
    if a.fs_deny:
        sandbox.ensure_clean_env()
    reports = [validate(c) for c in a.cases]
    if a.out:
        Path(a.out).write_text(json.dumps(reports, indent=2))
    for r in reports:
        bad = {k: v["stage"] for k, v in r["known_bad"].items()}
        failed = [k for k, v in r["gates"].items() if not v]
        print(f"{r['case']}: {'VALID' if r['valid'] else 'INVALID'} failed_gates={failed} "
              f"naive_passes_visible={r['naive_passes_visible']} known_good={r['known_good'] and r['known_good']['stage']} "
              f"known_bad_rejected_at={bad}")
