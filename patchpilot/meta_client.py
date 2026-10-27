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


def chat(messages: list, model: str, *, reasoning_effort: str | None = None, timeout_s: float = 120.0) -> dict:
    payload: dict = {"model": model, "messages": messages}
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    return _request("POST", "/chat/completions", payload, timeout_s)


def text_of(resp: dict) -> str:
    return resp["choices"][0]["message"]["content"]


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "models"
    if cmd == "models":
        print(json.dumps(list_models(), indent=2)[:4000])
    elif cmd == "ping":
        model = sys.argv[2]
        resp = chat([{"role": "user", "content": "Reply with exactly: pong"}], model, reasoning_effort="low")
        print(text_of(resp))
        print("usage:", json.dumps(resp.get("usage")))
    else:
        sys.exit("usage: python -m patchpilot.meta_client [models | ping <model>]")
