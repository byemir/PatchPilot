"""Minimal Meta Model API client (Chat Completions format). Standard library only."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = "https://api.meta.ai/v1"  # fixed on purpose: the key must never be sent elsewhere


class MetaAPIError(RuntimeError):
    pass


def _key() -> str:
    key = os.environ.get("MODEL_API_KEY") or os.environ.get("META_API_KEY")
    if not key:
        raise MetaAPIError("Set MODEL_API_KEY in your shell environment (never commit it).")
    return key


def _request(method: str, path: str, payload: dict | None = None, timeout_s: float = 120.0) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {_key()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:1000]
        raise MetaAPIError(f"HTTP {e.code} on {path}: {body}") from None
    except urllib.error.URLError as e:
        raise MetaAPIError(f"Network error on {path}: {e.reason}") from None


def list_models() -> dict:
    return _request("GET", "/models")


def chat(messages: list, model: str, *, reasoning_effort: str | None = None, timeout_s: float = 120.0,
         tools: list | None = None, tool_choice: str | dict | None = None) -> dict:
    payload: dict = {"model": model, "messages": messages}
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    if tools is not None:
        payload["tools"] = tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    return _request("POST", "/chat/completions", payload, timeout_s)


def message_of(resp: dict) -> dict:
    return resp["choices"][0]["message"]


def text_of(resp: dict) -> str:
    content = message_of(resp)["content"]
    return "" if content is None else content


ECHO_TOOL = {"type": "function", "function": {
    "name": "echo", "description": "Return the given text unchanged.",
    "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}}


def _show_turn(label: str, resp: dict) -> None:
    msg = message_of(resp)
    usage = resp.get("usage") or {}
    print(f"--- {label}")
    print("finish_reason:", resp["choices"][0].get("finish_reason"))
    content = msg.get("content")
    print("content is None:", content is None)
    if content is not None:
        print("content:", str(content)[:500])
    print("message keys:", sorted(msg.keys()))
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        args = fn.get("arguments")
        if isinstance(args, str):
            try:
                json.loads(args)
                valid = "valid JSON string"
            except ValueError:
                valid = "NOT valid JSON"
        else:
            valid = "not a string: " + type(args).__name__
        print(f"tool call id={tc.get('id')!r} name={fn.get('name')!r} arguments ({valid}): {str(args)[:300]}")
    print("usage:", json.dumps(usage))
    print("reasoning_tokens:", (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"))


def toolprobe(model: str) -> int:
    tools = [ECHO_TOOL]
    messages = [{"role": "user", "content": "Call the echo tool with text \"hello\", then tell me what it returned."}]
    print(f"=== toolprobe {model} reasoning_effort=low")
    stage = "turn 1"
    try:
        r1 = chat(messages, model, reasoning_effort="low", tools=tools)
        _show_turn("turn 1", r1)
        m1 = message_of(r1)
        calls = m1.get("tool_calls") or []
        if not calls:
            print("turn 2 skipped: no tool_calls in turn 1")
            return 0
        stage = "turn 2"
        messages.append(m1)
        for tc in calls:
            messages.append({"role": "tool", "tool_call_id": tc.get("id"), "content": "hello"})
        r2 = chat(messages, model, reasoning_effort="low", tools=tools)
        _show_turn("turn 2", r2)
    except Exception as e:
        print(f"ERROR in {stage}: {type(e).__name__}: {e}")
        return 1
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "models"
    if cmd == "models":
        print(json.dumps(list_models(), indent=2)[:4000])
    elif cmd == "ping":
        model = sys.argv[2]
        resp = chat([{"role": "user", "content": "Reply with exactly: pong"}], model, reasoning_effort="low")
        print(text_of(resp))
        print("usage:", json.dumps(resp.get("usage")))
    elif cmd == "toolprobe":
        if len(sys.argv) < 3:
            sys.exit("usage: python -m patchpilot.meta_client toolprobe <model>")
        sys.exit(toolprobe(sys.argv[2]))
    else:
        sys.exit("usage: python -m patchpilot.meta_client [models | ping <model> | toolprobe <model>]")
