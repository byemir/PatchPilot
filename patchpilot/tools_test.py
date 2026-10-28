"""Offline tests of the tools mode: no model, no network; model replies are faked. Model code runs in the sandbox.

    python -m patchpilot.tools_test
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from patchpilot import agent, meta_client, sandbox, tools

CASE = Path("benchmarks/p4_label_histogram")
FAILS: list = []


def check(label, ok, detail=""):
    print(("ok:   " if ok else "FAIL: ") + label + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(label)


def tool_reply(*calls):
    tcs = [{"id": f"call_{i}", "type": "function", "function": {"name": n, "arguments": json.dumps(a)}}
           for i, (n, a) in enumerate(calls)]
    return {"choices": [{"finish_reason": "tool_calls",
                         "message": {"role": "assistant", "content": None, "tool_calls": tcs}}],
            "usage": {"total_tokens": 100}}


def text_reply(text):
    return {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
            "usage": {"total_tokens": 50}}


def script(replies):
    it = iter(replies)
    seen: list = []

    def fake_chat(messages, model, **kw):
        seen.append({"tools": kw.get("tools") is not None})
        return next(it)

    return fake_chat, seen


def main() -> int:
    sandbox.ensure_clean_env()
    cfg = json.loads((CASE / "case.json").read_text())
    old_py, new_py = os.path.abspath(cfg["old"]), os.path.abspath(cfg["new"])
    editable, _ = agent.collect(CASE)
    good = json.loads((CASE / "known_good.json").read_text())["files"]
    probes = json.loads((CASE / "inputs.json").read_text())
    ctx = {"case_dir": CASE, "old_py": old_py, "new_py": new_py, "editable": editable}

    print("== tools")
    ws = tools._workspace(CASE, {})
    try:
        names = sandbox.ANSWER_KEYS + (sandbox.HIDDEN_INPUTS,)
        present = sorted(p.name for p in ws.rglob("*") if p.name in names)
    finally:
        sandbox.cleanup(ws)
    check("tool workspace holds no answer keys or hidden inputs", not present, str(present))
    r = json.loads(tools.call("run_probe", {"probes": probes}, ctx))
    check("run_probe without files: the original code on the new library differs from the original on the old",
          "results" in r and r["equal_count"] < r["total"], str(r)[:200])
    r = json.loads(tools.call("run_probe", {"probes": probes, "files": good}, ctx))
    check("run_probe with the known-good files: every input equal",
          "results" in r and r["equal_count"] == r["total"] and r["total"] == len(probes), str(r)[:200])
    r = json.loads(tools.call("run_tests", {"files": good}, ctx))
    check("run_tests with the known-good files: pass on both versions",
          bool(r.get("old_library", {}).get("passed")) and bool(r.get("new_library", {}).get("passed")), str(r)[:200])
    for label, name, args in (
            ("51 inputs rejected", "run_probe", {"probes": [[["t", "a"]]] * 51}),
            ("non-editable file rejected", "run_probe", {"probes": probes[:1], "files": {"run_case.py": "print(1)"}}),
            ("oversized input rejected", "run_probe", {"probes": ["x" * 3000]}),
            ("unknown tool rejected", "nope", {}),
            ("non-object arguments rejected", "run_probe", "not an object")):
        check(label, "error" in json.loads(tools.call(name, args, ctx)))
    os.environ["FAKE_SECRET"] = "x"
    try:
        tools.call("run_tests", {}, ctx)
        check("a secret-looking variable in the environment stops the tools", False, "no exception")
    except sandbox.SandboxUnavailable:
        check("a secret-looking variable in the environment stops the tools", True)
    finally:
        del os.environ["FAKE_SECRET"]

    print("== conversations through agent.repair(tools=True), faked model")
    final = json.dumps({"diagnosis": "fake", "files": good})

    def attempt(replies, **kw):
        fake, seen = script(replies)
        meta_client.chat = fake
        res = agent.repair(CASE, cfg["old"], cfg["new"], lib=cfg["lib"], runs_root=tempfile.mkdtemp(),
                           tools=True, **kw)
        rec = json.loads((Path(res["run_dir"]) / "attempt_1.json").read_text())
        return res, rec, seen

    res, rec, seen = attempt([tool_reply(("run_probe", {"probes": probes})),
                              tool_reply(("run_tests", {"files": good})), text_reply(final)])
    check("A: accepted on attempt 1 through the full gate", bool(res.get("success")) and res.get("attempts") == 1,
          str(res)[:200])
    check("A: 2 tool calls, 250 tokens, record fields", rec.get("tool_calls") == 2 and res.get("tokens_used") == 250
          and rec.get("tools") is True and rec.get("fs_deny") is True and rec.get("submitted_from") == "final reply",
          str({k: rec.get(k) for k in ("tool_calls", "tools", "fs_deny", "submitted_from")}))
    roles = [m["role"] for m in rec["messages"]]
    check("A: conversation roles", roles == ["system", "user", "assistant", "tool", "assistant", "tool", "assistant"],
          str(roles))
    check("A: tools offered in every call", all(s["tools"] for s in seen))

    res, rec, seen = attempt([tool_reply(("run_probe", {"probes": probes[:1]})) for _ in range(12)]
                             + [text_reply(final)])
    check("B: the call limit ends the tool turns; the last call carries no tools",
          bool(res.get("success")) and rec.get("tool_calls") == 12 and len(seen) == 13 and not seen[-1]["tools"],
          str({"calls": rec.get("tool_calls"), "model_calls": len(seen)}))
    check("B: a nudge message precedes the final reply",
          rec["messages"][-2]["role"] == "user" and "limit" in rec["messages"][-2]["content"])

    res, rec, seen = attempt([tool_reply(("run_tests", {"files": good})), text_reply("I give up")])
    check("C: an invalid final reply falls back to the last files passed to a tool",
          bool(res.get("success")) and rec.get("submitted_from") == "last_tool_files", str(res)[:200])

    res, rec, seen = attempt([tool_reply(("run_probe", {"probes": probes[:1], "files": {"run_case.py": "x"}})),
                              text_reply("nothing")], max_attempts=1)
    check("D: a write to a non-editable file is refused through the loop",
          any("not an editable file" in m.get("content", "") for m in rec["messages"] if m["role"] == "tool")
          and not res.get("success"))

    res, rec, seen = attempt([tool_reply(("run_probe", {"probes": probes[:1]})) for _ in range(8)],
                             max_attempts=1, token_budget=250)
    check("E: the token budget stops the conversation", rec.get("turn_stop") == "token budget",
          str(rec.get("turn_stop")))

    print("\n" + ("all checks passed" if not FAILS else f"{len(FAILS)} check(s) failed: {FAILS}"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
