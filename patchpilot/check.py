"""Detect silent breakage: tests pass on a library version but output differs from the golden output."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from patchpilot import sandbox


def check(case_dir: str | Path, python: str | Path,
          inputs: str = "inputs.json", golden: str = "golden.json", files: dict | None = None) -> dict:
    """case_dir must be the ORIGINAL case directory: the expected output is read from it and never from
    the workspace. `files` (editable path -> content) is written into the workspace before running."""
    case_dir = Path(case_dir)
    expected = json.loads((case_dir / golden).read_text())
    hide = sandbox.ANSWER_KEYS + (() if inputs == sandbox.HIDDEN_INPUTS else (sandbox.HIDDEN_INPUTS,))
    ws = sandbox.workspace(case_dir, exclude=hide)
    try:
        root = ws.resolve()
        for rel, content in (files or {}).items():
            target = (ws / rel).resolve()
            if root not in target.parents:
                raise ValueError(f"path outside the workspace: {rel}")
            target.write_text(content)
        tests = sandbox.run(python, ["-m", "pytest", "-q", "-p", "no:cacheprovider"], ws, timeout_s=120)
        run = sandbox.run(python, ["run_case.py", inputs], ws, timeout_s=60)
    finally:
        sandbox.cleanup(ws)

    tests_pass = tests.returncode == 0
    try:
        actual = json.loads(run.stdout) if run.returncode == 0 else None
    except json.JSONDecodeError:
        actual = None

    if not tests_pass:
        verdict = "LOUD_FAILURE"
    elif actual is None:
        verdict = "RUN_ERROR"
    elif actual == expected:
        verdict = "OK"
    else:
        verdict = "SILENT_BREAKAGE"

    return {
        "case": case_dir.name,
        "verdict": verdict,
        "tests_pass": tests_pass,
        "golden": expected,
        "actual": actual,
        "tests_duration_s": tests.duration_s,
        "run_stderr": run.stderr[-500:],
    }


if __name__ == "__main__":
    inputs = sys.argv[3] if len(sys.argv) > 3 else "inputs.json"
    golden = sys.argv[4] if len(sys.argv) > 4 else "golden.json"
    print(json.dumps(check(sys.argv[1], sys.argv[2], inputs, golden), indent=2))
