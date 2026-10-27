"""Repair loop: reproduce -> diagnose -> patch -> verify on the OLD and the NEW library version."""
from __future__ import annotations

import argparse
import difflib
import json
import re
import tempfile
import time
from pathlib import Path

from patchpilot import check, meta_client, sandbox

# The agent may never edit tests, the runner or the golden output (no "fixing" by cheating).
PROTECTED = {"golden.json", "run_case.py"}

SYSTEM = (
    "You are a careful Python maintainer repairing code that broke silently after a library upgrade. "
    "Reply with a single JSON object and nothing else."
)


def collect(case_dir: Path) -> tuple[dict, dict]:
    editable: dict = {}
    readonly: dict = {}
    for p in sorted(case_dir.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        text = p.read_text()
        if not text.strip():
            continue
        rel = p.relative_to(case_dir).as_posix()
        if rel in PROTECTED or rel.startswith("tests/"):
            readonly[rel] = text
        else:
            editable[rel] = text
    return editable, readonly


def lib_version(python: str | Path, lib: str) -> str:
    r = sandbox.run(python, ["-c", f"import {lib}; print({lib}.__version__)"], tempfile.gettempdir(), timeout_s=60)
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def build_prompt(lib, old_v, new_v, golden, actual, editable, readonly, feedback) -> str:
    parts = [
        f"A Python project's output changed after upgrading {lib} from {old_v} (correct behavior) "
        f"to {new_v}, and its tests still pass.",
        "Change ONLY the editable files so that the program prints the golden output on the NEW version "
        "and still prints the golden output on the OLD version.",
        f"Golden output: {json.dumps(golden)}",
        f"Actual output on {new_v}: {json.dumps(actual)}",
        "",
        "EDITABLE FILES:",
    ]
    for rel, text in editable.items():
        parts.append(f"--- {rel} ---\n{text}")
    parts.append("READ-ONLY FILES (never change these):")
    for rel, text in readonly.items():
        parts.append(f"--- {rel} ---\n{text}")
    if feedback:
        parts.append("YOUR PREVIOUS ATTEMPT FAILED:\n" + feedback)
    parts.append(
        'Reply with JSON: {"diagnosis": "<root cause in one or two sentences>", '
        '"files": {"<editable path>": "<complete new file content>"}}. Include only files you change.'
    )
    return "\n".join(parts)


def parse_reply(text: str, editable: dict) -> tuple[str, dict]:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in reply")
    data = json.loads(m.group(0))
    files = data.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("reply has no 'files' object")
    for path, content in files.items():
        if path not in editable:
            raise ValueError(f"not an editable file: {path}")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"empty or non-text content for {path}")
    return str(data.get("diagnosis", "")), files


def make_diff(original: dict, files: dict) -> str:
    out: list = []
    for rel, new in files.items():
        out.extend(
            difflib.unified_diff(original[rel].splitlines(True), new.splitlines(True), f"a/{rel}", f"b/{rel}")
        )
    return "".join(out)


def repair(case_dir, old_py, new_py, *, lib="pandas", model="muse-spark-1.3", effort="low",
           max_attempts=3, token_budget=60000, runs_root="runs") -> dict:
    case_dir = Path(case_dir)
    old0 = check.check(case_dir, old_py)
    new0 = check.check(case_dir, new_py)
    if old0["verdict"] != "OK" or new0["verdict"] != "SILENT_BREAKAGE":
        return {"success": False, "reason": "not a silent breakage",
                "old": old0["verdict"], "new": new0["verdict"]}

    run_dir = Path(runs_root) / f"{time.strftime('%Y%m%d-%H%M%S')}_{case_dir.name}"
    run_dir.mkdir(parents=True)
    editable, readonly = collect(case_dir)
    old_v, new_v = lib_version(old_py, lib), lib_version(new_py, lib)

    used = 0
    feedback = ""
    for attempt in range(1, max_attempts + 1):
        if used >= token_budget:
            return {"success": False, "reason": "token budget exhausted", "tokens_used": used, "run_dir": str(run_dir)}
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": build_prompt(lib, old_v, new_v, new0["golden"], new0["actual"],
                                                     editable, readonly, feedback)},
        ]
        resp = meta_client.chat(messages, model, reasoning_effort=effort, timeout_s=240)
        usage = resp.get("usage") or {}
        used += int(usage.get("total_tokens", 0))
        text = meta_client.text_of(resp)
        record = {"attempt": attempt, "model": model, "effort": effort, "messages": messages,
                  "reply": text, "usage": usage}

        try:
            diagnosis, files = parse_reply(text, editable)
        except ValueError as e:
            record["error"] = str(e)
            feedback = f"Your reply was invalid: {e}"
            (run_dir / f"attempt_{attempt}.json").write_text(json.dumps(record, indent=2))
            continue

        ws = sandbox.workspace(case_dir)
        try:
            for rel, content in files.items():
                (ws / rel).write_text(content)
            old_r = check.check(ws, old_py)
            new_r = check.check(ws, new_py)
        finally:
            sandbox.cleanup(ws)

        ok = old_r["verdict"] == "OK" and new_r["verdict"] == "OK"
        record.update({"diagnosis": diagnosis, "files": files,
                       "old_verdict": old_r["verdict"], "new_verdict": new_r["verdict"],
                       "old_actual": old_r["actual"], "new_actual": new_r["actual"], "success": ok})
        (run_dir / f"attempt_{attempt}.json").write_text(json.dumps(record, indent=2))

        if ok:
            diff = make_diff(editable, files)
            (run_dir / "patch.diff").write_text(diff)
            return {"success": True, "attempts": attempt, "tokens_used": used, "diagnosis": diagnosis,
                    "diff": diff, "run_dir": str(run_dir)}

        feedback = (
            f"After your change: on {old_v} verdict={old_r['verdict']} output={old_r['actual']}; "
            f"on {new_v} verdict={new_r['verdict']} output={new_r['actual']}. "
            f"stderr: {new_r['run_stderr'] or old_r['run_stderr']}"
        )

    return {"success": False, "reason": "max attempts reached", "tokens_used": used, "run_dir": str(run_dir)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("case_dir")
    ap.add_argument("old_python")
    ap.add_argument("new_python")
    ap.add_argument("--lib", default="pandas")
    ap.add_argument("--model", default="muse-spark-1.3")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--token-budget", type=int, default=60000)
    a = ap.parse_args()
    result = repair(a.case_dir, a.old_python, a.new_python, lib=a.lib, model=a.model, effort=a.effort,
                    max_attempts=a.max_attempts, token_budget=a.token_budget)
    diff = result.pop("diff", "")
    print(json.dumps(result, indent=2))
    if diff:
        print(diff)
