"""Tools offered to the model in --tools mode (run_tests, run_probe) and the conversation loop around them.

Both tools run through sandbox.run, i.e. under the same OS layer, clean environment and fail-closed checks as the
gate. Their workspace never holds the answer keys or the hidden inputs. run_probe takes data only (inputs in the
format of inputs.json), never code; it is an oracle for the ORIGINAL behavior (original code on the old library)
on inputs the model chooses.
"""
from __future__ import annotations

import json
import time

from patchpilot import differential, meta_client, sandbox

MAX_CALLS = 12            # tool calls per attempt
ATTEMPT_SECONDS = 300     # wall clock per attempt (model calls and tools)
MAX_PROBES = 50
MAX_PROBE_BYTES = 2048    # per input
MAX_TOTAL_PROBE_BYTES = 32768
MAX_FILE_BYTES = 100_000
OUT_CHARS = 600
TEST_TAIL = 1500

_FILES = {"type": "object", "additionalProperties": {"type": "string"},
          "description": "Optional candidate: maps an editable file path to its complete new content. "
                         "Without it the original code is used."}
SPEC = [
    {"type": "function", "function": {
        "name": "run_tests",
        "description": "Run the project's test suite on the OLD and on the NEW library.",
        "parameters": {"type": "object", "properties": {"files": _FILES}, "required": []}}},
    {"type": "function", "function": {
        "name": "run_probe",
        "description": "Run inputs you choose through the ORIGINAL code on the OLD library and through the candidate "
                       "on the NEW library, and compare the outputs. Each input is the value that run_case.py passes "
                       "to the project's function for one input (data only, no code); at most 50 inputs, 2 KB each.",
        "parameters": {"type": "object",
                       "properties": {"probes": {"type": "array", "items": {}}, "files": _FILES},
                       "required": ["probes"]}}},
]


class ToolError(ValueError):
    pass


def _check_files(files, editable) -> dict:
    if files is None:
        return {}
    if not isinstance(files, dict):
        raise ToolError("files must be an object that maps an editable file path to its complete new content")
    for path, content in files.items():
        if path not in editable:
            raise ToolError(f"not an editable file: {path}")
        if not isinstance(content, str) or not content.strip():
            raise ToolError(f"empty or non-text content for {path}")
        if len(content.encode()) > MAX_FILE_BYTES:
            raise ToolError(f"content of {path} is larger than {MAX_FILE_BYTES} bytes")
    return files


def _workspace(case_dir, files):
    ws = sandbox.workspace(case_dir, exclude=sandbox.ANSWER_KEYS + (sandbox.HIDDEN_INPUTS,))
    for rel, content in files.items():
        (ws / rel).write_text(content)
    return ws


def _short(value):
    text = json.dumps(value)
    return value if len(text) <= OUT_CHARS else text[:OUT_CHARS] + "...(truncated)"


def run_tests(ctx, files=None) -> dict:
    files = _check_files(files, ctx["editable"])
    out = {}
    for label, py in (("old_library", ctx["old_py"]), ("new_library", ctx["new_py"])):
        ws = _workspace(ctx["case_dir"], files)
        try:
            r = sandbox.run(py, ["-m", "pytest", "-q", "-p", "no:cacheprovider"], ws, timeout_s=120)
        finally:
            sandbox.cleanup(ws)
        out[label] = {"passed": r.returncode == 0, "timed_out": r.timed_out,
                      "output_tail": (r.stdout + r.stderr)[-TEST_TAIL:]}
    return out


def run_probe(ctx, probes, files=None) -> dict:
    files = _check_files(files, ctx["editable"])
    if not isinstance(probes, list) or not probes:
        raise ToolError("probes must be a non-empty list of inputs")
    if len(probes) > MAX_PROBES:
        raise ToolError(f"at most {MAX_PROBES} inputs per call")
    try:
        sizes = [len(json.dumps(p)) for p in probes]
    except (TypeError, ValueError):
        raise ToolError("inputs must be JSON data") from None
    if max(sizes) > MAX_PROBE_BYTES or sum(sizes) > MAX_TOTAL_PROBE_BYTES:
        raise ToolError(f"an input is larger than {MAX_PROBE_BYTES} bytes or the total is larger than "
                        f"{MAX_TOTAL_PROBE_BYTES} bytes")
    ref, e1 = differential._run(ctx["case_dir"], None, ctx["old_py"], probes, 60)
    cand, e2 = differential._run(ctx["case_dir"], files, ctx["new_py"], probes, 60)
    if ref is None or cand is None:
        return {"error": "could not run the inputs: " + (e1 or e2)}
    items = [{"index": i, "original_on_old_library": _short(a), "candidate_on_new_library": _short(b),
              "equal": differential._same(a, b)} for i, (a, b) in enumerate(zip(ref, cand))]
    return {"results": items, "equal_count": sum(1 for x in items if x["equal"]), "total": len(items)}


def call(name, args, ctx) -> str:
    try:
        if not isinstance(args, dict):
            raise ToolError("arguments must be a JSON object")
        if name == "run_tests":
            res = run_tests(ctx, args.get("files"))
        elif name == "run_probe":
            res = run_probe(ctx, args.get("probes"), args.get("files"))
        else:
            raise ToolError(f"unknown tool: {name}")
    except ToolError as e:
        res = {"error": str(e)}
    except sandbox.SandboxUnavailable:
        raise
    except Exception as e:
        res = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    return json.dumps(res)


def converse(messages, model, effort, ctx, *, token_left, max_calls=MAX_CALLS, deadline_s=ATTEMPT_SECONDS) -> dict:
    """Run one attempt as a tool conversation. `messages` is extended in place (assistant, tool and nudge messages)."""
    t0 = time.monotonic()
    total = calls = 0
    usages: list = []
    log: list = []
    last_files = None
    text, stop = "", "final reply"
    for _turn in range(max_calls + 3):
        if total >= token_left:
            stop = "token budget"
            break
        if time.monotonic() - t0 > deadline_s:
            stop = "attempt time limit"
            break
        resp = meta_client.chat(messages, model, reasoning_effort=effort, timeout_s=240,
                                tools=SPEC if calls < max_calls else None)
        usage = resp.get("usage") or {}
        usages.append(usage)
        total += int(usage.get("total_tokens", 0))
        msg = meta_client.message_of(resp)
        messages.append(msg)
        pending = msg.get("tool_calls") or []
        if not pending:
            text = meta_client.text_of(resp)
            break
        for tc in pending:
            fn = tc.get("function") or {}
            name, raw = fn.get("name"), fn.get("arguments")
            t1 = time.monotonic()
            if calls >= max_calls:
                result = json.dumps({"error": "tool call limit reached; reply with the final JSON object now"})
            else:
                calls += 1
                try:
                    args = json.loads(raw) if raw else {}
                except ValueError:
                    args = None
                if args is None:
                    result = json.dumps({"error": "arguments are not valid JSON"})
                else:
                    if isinstance(args, dict) and isinstance(args.get("files"), dict):
                        try:
                            last_files = _check_files(args["files"], ctx["editable"])
                        except ToolError:
                            pass
                    result = call(name, args, ctx)
            log.append({"name": name, "seconds": round(time.monotonic() - t1, 2), "result_chars": len(result)})
            messages.append({"role": "tool", "tool_call_id": tc.get("id"), "content": result})
        if calls >= max_calls:
            messages.append({"role": "user",
                             "content": "Tool call limit reached. Reply now with the final JSON object only."})
    else:
        stop = "turn limit"
    return {"text": text, "usage_total": total, "usages": usages, "tool_calls": calls, "tool_log": log,
            "last_files": last_files, "stop": stop, "submitted_from": "final reply"}
