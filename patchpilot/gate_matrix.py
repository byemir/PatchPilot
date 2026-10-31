"""Gate matrix: what does each gate catch? No model, no network, repeatable.

Every patch (the known-good one, the known-bad ones, and one generated "overfit" patch per case that memorizes the
visible outputs) goes through the three gates independently, so the table shows what a workflow with only the
visible tests, with visible plus hidden tests, and with all three gates would have accepted.

  visible      OLD and NEW library both reproduce the golden output on the visible inputs (tests green)
  hidden       the same on held-out inputs the model never sees
  differential generated inputs: patched code on both libraries against the original code on the old library

The overfit patch is the original code plus a wrapper that, only when run_case.py reads inputs.json, returns the
recorded golden outputs (copied into the patch text); for every other input it calls the original code. It is the
cheapest possible cheat that still satisfies the visible check.

  python -m patchpilot.gate_matrix [benchmarks/<case> ...] [--out report.json] [--md table.md] [--n 200] [--fs-deny]

Run from the repository root with the pinned environments built (scripts/setup_envs.sh).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from patchpilot import check, differential, sandbox

OVERFIT = '''
import json as _json, os as _os, sys as _sys
_orig = __FN__
_mem = _json.loads(__MEM__)
_pos = [0]


def __FN__(*a, **k):
    if (_sys.argv and _os.path.basename(_sys.argv[0]) == "run_case.py" and len(_sys.argv) > 1
            and _os.path.basename(_sys.argv[1]) == "inputs.json" and _pos[0] < len(_mem)):
        i = _pos[0]
        _pos[0] += 1
        return _mem[i]
    return _orig(*a, **k)
'''

DIFF_REJECT = ("DIVERGENCE", "RUN_ERROR")


def build_overfit(case_dir: Path) -> dict | None:
    """Files of the overfit patch for one case, or None when the case does not have the usual shape."""
    case_dir = Path(case_dir)
    try:
        runner = (case_dir / "run_case.py").read_text()
        m = re.search(r"^from (\w+) import (\w+)", runner, re.M)
        if not m:
            return None
        module, fn = m.groups()
        src = (case_dir / f"{module}.py").read_text()
        golden = json.loads((case_dir / "golden.json").read_text())
    except (OSError, ValueError):
        return None
    code = OVERFIT.replace("__FN__", fn).replace("__MEM__", repr(json.dumps(golden)))
    return {f"{module}.py": src + "\n" + code}


def gates(case_dir: Path, old_py: str, new_py: str, files: dict, n: int = 200) -> dict:
    """The three gates, each judged on its own (the pipeline stops at the first failure; this does not)."""
    vo, vn = check.check(case_dir, old_py, files=files), check.check(case_dir, new_py, files=files)
    ho = check.check(case_dir, old_py, "hidden_inputs.json", "hidden_golden.json", files=files)
    hn = check.check(case_dir, new_py, "hidden_inputs.json", "hidden_golden.json", files=files)
    visible = vo["verdict"] == "OK" and vn["verdict"] == "OK"
    hidden = ho["verdict"] == "OK" and hn["verdict"] == "OK"
    try:
        d = differential.differential(case_dir, old_py, new_py, files, n=n)
        verdict = d.get("verdict")
    except Exception as e:  # a patch that cannot even be imported is a rejection, not a crash of the table
        d, verdict = {}, f"RUN_ERROR ({type(e).__name__})"
    diff_ok = verdict not in DIFF_REJECT and not str(verdict).startswith("RUN_ERROR")
    return {"visible": visible, "hidden": hidden, "differential": verdict, "differential_ok": diff_ok,
            "valid_probes": d.get("valid"), "visible_new": vn["verdict"], "hidden_new": hn["verdict"]}


def first_stop(g: dict) -> str:
    if not g["visible"]:
        return "visible"
    if not g["hidden"]:
        return "hidden"
    if not g["differential_ok"]:
        return "differential"
    return "accepted"


def case_rows(case_dir: Path, n: int = 200) -> list[dict]:
    case_dir = Path(case_dir)
    cfg = json.loads((case_dir / "case.json").read_text())
    old_py, new_py = os.path.abspath(cfg["old"]), os.path.abspath(cfg["new"])
    patches: list[tuple[str, str, dict | None]] = []
    good = case_dir / "known_good.json"
    if good.exists():
        patches.append(("known_good", "good", json.loads(good.read_text())["files"]))
    for p in sorted((case_dir / "known_bad").glob("*.json")):
        patches.append((p.stem, "bad", json.loads(p.read_text())["files"]))
    patches.append(("overfit_visible_outputs", "overfit", build_overfit(case_dir)))
    rows = []
    for name, kind, files in patches:
        if files is None:
            rows.append({"case": case_dir.name, "patch": name, "kind": kind, "skipped": "no usual run_case.py shape"})
            continue
        g = gates(case_dir, old_py, new_py, files, n=n)
        rows.append({"case": case_dir.name, "patch": name, "kind": kind, **g, "stopped_at": first_stop(g)})
        print(f"{case_dir.name:28} {name:26} {kind:8} visible={g['visible']!s:5} hidden={g['hidden']!s:5} "
              f"differential={g['differential']} -> {rows[-1]['stopped_at']}", flush=True)
    return rows


def summarize(rows: list[dict]) -> dict:
    """Counts per kind of patch: how many each kind of workflow would have accepted."""
    out: dict = {}
    for kind in ("good", "bad", "overfit"):
        part = [r for r in rows if r["kind"] == kind and "skipped" not in r]
        out[kind] = {
            "patches": len(part),
            "accepted_by_visible_only": sum(r["visible"] for r in part),
            "accepted_by_visible_and_hidden": sum(r["visible"] and r["hidden"] for r in part),
            "accepted_by_all_three": sum(r["visible"] and r["hidden"] and r["differential_ok"] for r in part),
            "rejected_first_at": {s: sum(r["stopped_at"] == s for r in part) for s in ("visible", "hidden", "differential")},
        }
    out["skipped"] = sum("skipped" in r for r in rows)
    # bad patches that only the hidden gate or only the differential gate stopped
    bad = [r for r in rows if r["kind"] != "good" and "skipped" not in r]
    out["needed_hidden"] = sum(r["visible"] and not r["hidden"] for r in bad)
    out["needed_differential"] = sum(r["visible"] and r["hidden"] and not r["differential_ok"] for r in bad)
    return out


def to_markdown(rows: list[dict], s: dict) -> str:
    def yn(v: bool) -> str:
        return "pass" if v else "FAIL"
    lines = ["# Gate matrix", "",
             "Generated by `python -m patchpilot.gate_matrix`. No model, no network. Each patch is judged by each gate on its "
             "own; \"stopped at\" is the first gate the pipeline would fail it at.", "",
             "| kind | patches | accepted by visible tests only | by visible + hidden | by all three gates |",
             "|---|---|---|---|---|"]
    names = {"good": "known-good patch", "bad": "known-bad patches (hand written)", "overfit": "overfit patch (memorizes visible outputs)"}
    for k in ("good", "bad", "overfit"):
        v = s[k]
        lines.append(f"| {names[k]} | {v['patches']} | {v['accepted_by_visible_only']} | "
                     f"{v['accepted_by_visible_and_hidden']} | {v['accepted_by_all_three']} |")
    lines += ["", f"Wrong patches that pass the visible tests and were stopped by the hidden tests: {s['needed_hidden']}. "
              f"Wrong patches that pass visible and hidden and were stopped by the differential gate: {s['needed_differential']}. "
              f"Cases skipped (no usual run_case.py shape): {s['skipped']}.", "",
              "| case | patch | kind | visible | hidden | differential | stopped at |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        if "skipped" in r:
            lines.append(f"| {r['case']} | {r['patch']} | {r['kind']} | skipped | skipped | skipped | {r['skipped']} |")
        else:
            lines.append(f"| {r['case']} | {r['patch']} | {r['kind']} | {yn(r['visible'])} | {yn(r['hidden'])} | "
                         f"{r['differential']} | {r['stopped_at']} |")
    lines += ["", "Limits: synthetic cases written for this project; the bad patches are ours, so the table shows what the gates "
              "stop, not how often a model writes such a patch (see `docs/APP_RUNS.md` for model runs).", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cases", nargs="*", help="case folders (default: every folder in benchmarks/ with a case.json)")
    ap.add_argument("--out", help="write the full JSON report here")
    ap.add_argument("--md", help="write the markdown table here")
    ap.add_argument("--n", type=int, default=200, help="generated inputs for the differential gate")
    ap.add_argument("--fs-deny", action="store_true", help="run the fixtures under the OS file-system isolation too")
    a = ap.parse_args()
    sandbox.set_fs_deny(a.fs_deny)
    if a.fs_deny:
        sandbox.ensure_clean_env()
    cases = [Path(c) for c in a.cases] or sorted(p.parent for p in Path("benchmarks").glob("*/case.json"))
    rows: list[dict] = []
    for c in cases:
        rows += case_rows(c, n=a.n)
    s = summarize(rows)
    print(json.dumps(s, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps({"summary": s, "rows": rows}, indent=1))
    if a.md:
        Path(a.md).write_text(to_markdown(rows, s))
    # criteria: every known-good accepted, nothing wrong accepted by all three gates
    bad_accepted = s["bad"]["accepted_by_all_three"] + s["overfit"]["accepted_by_all_three"]
    good_rejected = s["good"]["patches"] - s["good"]["accepted_by_all_three"]
    if bad_accepted or good_rejected:
        print(f"CRITERION FAILED: wrong patches accepted by all three gates: {bad_accepted}; good patches rejected: {good_rejected}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
