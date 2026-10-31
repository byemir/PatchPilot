"""Repair loop: reproduce -> diagnose -> patch -> verify on the OLD and the NEW library version."""
from __future__ import annotations

import argparse
import difflib
import json
import re
import tempfile
import time
from pathlib import Path

from patchpilot import check, differential, meta_client, sandbox
from patchpilot import tools as tools_mod

# The agent may never edit tests, the runner or the golden output (no "fixing" by cheating).
PROTECTED = {"golden.json", "run_case.py"}

SYSTEM = (
    "You are a careful Python maintainer repairing code that broke silently after a library upgrade. "
    "Reply with a single JSON object and nothing else."
)
SYSTEM_TOOLS = (
    SYSTEM[: -len("Reply with a single JSON object and nothing else.")]
    + "You may call the provided tools to run the tests and to compare the original code (old library) with your "
    "candidate (new library) on inputs you choose; pass your candidate files to each tool call in the files argument. "
    "When you are done, reply with the final JSON object and nothing else."
)


PROJ_CONTEXT_CHARS = 30_000  # how much of the surrounding project is shown to the model as read-only context


def collect(case_dir: Path) -> tuple[dict, dict]:
    editable: dict = {}
    readonly: dict = {}
    proj_total = 0
    for p in sorted(case_dir.rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        text = p.read_text()
        if not text.strip():
            continue
        rel = p.relative_to(case_dir).as_posix()
        if rel.startswith("proj/"):  # project mode: the rest of the project is context only
            proj_total += len(text)
            if proj_total <= PROJ_CONTEXT_CHARS:
                readonly[rel] = text
        elif rel in PROTECTED or rel.startswith("tests/"):
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
           max_attempts=3, token_budget=60000, runs_root="runs", diff_check=True, diff_n=200,
           diff_seed=0, tools=False, endpoint=None, progress=None) -> dict:
    case_dir = Path(case_dir)
    if tools and endpoint:
        raise ValueError("tools mode is not supported with a local endpoint")
    old0 = check.check(case_dir, old_py)
    new0 = check.check(case_dir, new_py)
    if old0["verdict"] != "OK" or new0["verdict"] != "SILENT_BREAKAGE":
        return {"success": False, "reason": "not a silent breakage",
                "old": old0["verdict"], "new": new0["verdict"]}

    run_dir = Path(runs_root) / f"{time.strftime('%Y%m%d-%H%M%S')}_{case_dir.name}"
    run_dir.mkdir(parents=True)
    editable, readonly = collect(case_dir)
    tool_ctx = {"case_dir": case_dir, "old_py": old_py, "new_py": new_py, "editable": editable}
    old_v, new_v = lib_version(old_py, lib), lib_version(new_py, lib)
    has_hidden = (case_dir / "hidden_golden.json").exists()

    used = 0
    feedback = ""
    for attempt in range(1, max_attempts + 1):
        if used >= token_budget:
            return {"success": False, "reason": "token budget exhausted", "tokens_used": used, "run_dir": str(run_dir)}
        messages = [
            {"role": "system", "content": SYSTEM_TOOLS if tools else SYSTEM},
            {"role": "user", "content": build_prompt(lib, old_v, new_v, new0["golden"], new0["actual"],
                                                     editable, readonly, feedback)},
        ]
        if tools:
            conv = tools_mod.converse(messages, model, effort, tool_ctx, token_left=token_budget - used)
            usage = {"total_tokens": conv["usage_total"], "per_call": conv["usages"]}
            used += conv["usage_total"]
            text = conv["text"]
            try:
                parse_reply(text, editable)
            except ValueError:
                if conv["last_files"]:
                    text = json.dumps({"diagnosis": "(final reply missing or invalid; the last files passed to a tool "
                                                    "were submitted)", "files": conv["last_files"]})
                    conv["submitted_from"] = "last_tool_files"
        else:
            conv = None
            resp = meta_client.chat(messages, model, reasoning_effort=effort, timeout_s=900 if endpoint else 240,
                                    endpoint=endpoint)
            usage = resp.get("usage") or {}
            used += int(usage.get("total_tokens", 0))
            text = meta_client.text_of(resp)
        record = {"attempt": attempt, "model": model, "effort": effort, "messages": messages,
                  "reply": text, "usage": usage, "endpoint": endpoint}
        if conv:
            record.update({"tools": True, "tool_calls": conv["tool_calls"], "tool_log": conv["tool_log"],
                           "turn_stop": conv["stop"], "submitted_from": conv["submitted_from"]})

        try:
            diagnosis, files = parse_reply(text, editable)
        except ValueError as e:
            record["error"] = str(e)
            feedback = f"Your reply was invalid: {e}"
            (run_dir / f"attempt_{attempt}.json").write_text(json.dumps(record, indent=2))
            if progress:
                progress(attempt, record)
            continue

        old_r = check.check(case_dir, old_py, files=files)
        new_r = check.check(case_dir, new_py, files=files)
        hid_old = hid_new = None
        if has_hidden:
            hid_old = check.check(case_dir, old_py, "hidden_inputs.json", "hidden_golden.json", files=files)
            hid_new = check.check(case_dir, new_py, "hidden_inputs.json", "hidden_golden.json", files=files)

        visible_ok = old_r["verdict"] == "OK" and new_r["verdict"] == "OK"
        hidden_ok = (not has_hidden) or (hid_old["verdict"] == "OK" and hid_new["verdict"] == "OK")
        diff = None
        if visible_ok and hidden_ok and diff_check:
            diff = differential.differential(case_dir, old_py, new_py, files, n=diff_n, seed=diff_seed)
        diff_ok = diff is None or diff["verdict"] in ("PASS", "WEAK")
        ok = visible_ok and hidden_ok and diff_ok
        record.update({"fs_deny": sandbox.FS_DENY, "diagnosis": diagnosis, "files": files,
                       "old_verdict": old_r["verdict"], "new_verdict": new_r["verdict"],
                       "old_actual": old_r["actual"], "new_actual": new_r["actual"],
                       "hidden_old": hid_old and hid_old["verdict"],
                       "hidden_new": hid_new and hid_new["verdict"],
                       "hidden_new_actual": hid_new and hid_new["actual"], "differential": diff, "success": ok})
        (run_dir / f"attempt_{attempt}.json").write_text(json.dumps(record, indent=2))
        if progress:
            progress(attempt, record)

        if ok:
            patch = make_diff(editable, files)
            (run_dir / "patch.diff").write_text(patch)
            return {"success": True, "attempts": attempt, "tokens_used": used, "hidden_checked": has_hidden,
                    "diagnosis": diagnosis,
                    "differential": diff and {k: diff[k] for k in ("verdict", "generated", "valid",
                                                                    "core_divergences", "wide_divergences")},
                    "diff": patch, "run_dir": str(run_dir)}

        if visible_ok and hidden_ok and not diff_ok:
            ex = next((e for e in diff.get("examples", []) if e["tier"] == "core"), None) or {}
            feedback = (
                "Your patch passes the recorded checks but diverges from the original behavior on a generated "
                f"input. Input: {json.dumps(ex.get('probe'))}; expected (original code on {old_v}): "
                f"{json.dumps(ex.get('expected'))}; got (your code, {ex.get('where')}): {json.dumps(ex.get('got'))}. "
                f"{diff.get('core_divergences')} generated inputs diverge in total. Fix the root cause generally."
            ) if ex else f"Differential check could not run: {diff.get('reason')}"
        elif visible_ok and not hidden_ok:
            feedback = (
                "Your patch passes the visible checks but fails held-out checks on other inputs "
                "(details withheld). Fix the root cause generally instead of special-casing the visible inputs."
            )
        else:
            feedback = (
                f"After your change: on {old_v} verdict={old_r['verdict']} output={old_r['actual']}; "
                f"on {new_v} verdict={new_r['verdict']} output={new_r['actual']}. "
                f"stderr: {new_r['run_stderr'] or old_r['run_stderr']}"
            )

    return {"success": False, "reason": "max attempts reached", "tokens_used": used, "run_dir": str(run_dir)}


if __name__ == "__main__":
    sandbox.ensure_clean_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("case_dir")
    ap.add_argument("old_python")
    ap.add_argument("new_python")
    ap.add_argument("--lib", default="pandas")
    ap.add_argument("--model", default=None)
    ap.add_argument("--effort", default="low")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--token-budget", type=int, default=60000)
    ap.add_argument("--no-fs-deny", action="store_true",
                    help="run model code without OS file-system isolation (unsafe; runs are marked fs_deny=false)")
    ap.add_argument("--tools", action="store_true",
                    help="let the model call run_tests and run_probe (a tool conversation per attempt)")
    ap.add_argument("--endpoint", help="base URL of a local OpenAI-compatible server (loopback only, no API key is sent)")
    a = ap.parse_args()
    a.model = a.model or ("muse-glimmer" if a.endpoint else "muse-spark-1.3")
    if a.no_fs_deny and meta_client.KEY_PATH.exists():
        raise SystemExit("--no-fs-deny is refused while the key file exists (" + str(meta_client.KEY_PATH) +
                         "): model code run without the OS layer could read it.")
    sandbox.set_fs_deny(not a.no_fs_deny)
    result = repair(a.case_dir, a.old_python, a.new_python, lib=a.lib, model=a.model, effort=a.effort,
                    max_attempts=a.max_attempts, token_budget=a.token_budget, tools=a.tools, endpoint=a.endpoint)
    diff = result.pop("diff", "")
    print(json.dumps(result, indent=2))
    if diff:
        print(diff)
