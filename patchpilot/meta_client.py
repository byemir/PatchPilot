"""Minimal Meta Model API client (Chat Completions format). Standard library only."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

BASE_URL = "https://api.meta.ai/v1"  # fixed on purpose: the key must never be sent elsewhere
BASETEN_URL = "https://inference.baseten.co/v1"  # fixed too: Muse Spark Open, served by Baseten for the hackathon (its own key file)
BASETEN_MODELS = ("meta-models/muse-spark-open-1026",)  # the only model the hackathon Baseten key works with


class MetaAPIError(RuntimeError):
    pass


class MetaAuthError(MetaAPIError):
    pass


KEY_PATH = Path.home() / ".config" / "patchpilot" / "meta_key"
BASETEN_KEY_PATH = Path.home() / ".config" / "patchpilot" / "baseten_key"


def provider_of(model: str) -> str:
    """Which service a hosted model name goes to; each service has its own fixed URL and its own key file."""
    return "baseten" if model in BASETEN_MODELS else "meta"


def _key_path(provider: str) -> Path:
    return BASETEN_KEY_PATH if provider == "baseten" else KEY_PATH


def any_key_file() -> bool:
    """True if a key file for any hosted service exists (the isolation guards refuse to be switched off then)."""
    return KEY_PATH.exists() or BASETEN_KEY_PATH.exists()


def _key(provider: str = "meta") -> str:
    # The key lives in a file outside the repository, is read at call time, is never read from or written
    # to the environment and is never passed to a subprocess. A key is only ever sent to its own service.
    path = _key_path(provider)
    try:
        file_mode = path.stat().st_mode & 0o777
        dir_mode = path.parent.stat().st_mode & 0o777
    except OSError:
        raise MetaAuthError(f"Key file not found: {path} (directory mode 0700, file mode 0600; never commit it).") from None
    if file_mode & 0o077 or dir_mode & 0o077:
        raise MetaAuthError(f"Key file permissions are too open (file {oct(file_mode)}, directory {oct(dir_mode)}); use 0600 and 0700.")
    key = path.read_text().strip()
    if not key:
        raise MetaAuthError("Key file is empty.")
    return key


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # the Authorization header must not follow a redirect to another host


def _request(method: str, path: str, payload: dict | None = None, timeout_s: float = 120.0, provider: str = "meta") -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        (BASETEN_URL if provider == "baseten" else BASE_URL) + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {_key(provider)}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.build_opener(_NoRedirect()).open(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:1000]
        raise MetaAPIError(f"HTTP {e.code} on {path}: {body}") from None
    except urllib.error.URLError as e:
        raise MetaAPIError(f"Network error on {path}: {e.reason}") from None


def list_models() -> dict:
    return _request("GET", "/models")


LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
LOCAL_SAMPLING = {"temperature": 1.0, "top_p": 0.95, "top_k": 64}  # published Muse Glimmer settings; greedy decoding is advised against
LOCAL_REASONING = ("low", "medium", "high", "xhigh")  # reasoning_strength levels of the Muse Glimmer chat template
LOCAL_MAX_TOKENS = 12000  # hard cap: a runaway reasoning trace must not keep the single server slot busy past the 900 s client timeout


def _check_local(url: str) -> str:
    u = urlparse(url)
    if u.scheme != "http" or u.hostname not in LOCAL_HOSTS:
        raise MetaAPIError(f"local endpoint must be http on a loopback host (127.0.0.1, localhost or ::1): {url}")
    return url


def _local_request(url: str, method: str, payload: dict | None, timeout_s: float) -> dict:
    """Request to a server on this machine: no Authorization header, the API key is never read, no proxy, no redirects."""
    _check_local(url)
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", "Accept": "application/json"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(req, timeout=timeout_s) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise MetaAPIError(f"HTTP {e.code} on {url}: {e.read().decode(errors='replace')[:1000]}") from None
    except urllib.error.URLError as e:
        raise MetaAPIError(f"Network error on {url}: {e.reason}") from None


def _local_chat(endpoint, messages, model, reasoning_effort, timeout_s, tools, tool_choice) -> dict:
    payload: dict = {"model": model, "messages": messages, "max_tokens": LOCAL_MAX_TOKENS, **LOCAL_SAMPLING}
    if reasoning_effort:
        if reasoning_effort not in LOCAL_REASONING:
            raise ValueError(f"reasoning level {reasoning_effort!r} is not one of {LOCAL_REASONING}")
        payload["chat_template_kwargs"] = {"reasoning_strength": reasoning_effort}
    if tools is not None:
        payload["tools"] = tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    return _local_request(_check_local(endpoint).rstrip("/") + "/chat/completions", "POST", payload, timeout_s)


def local_server_info(endpoint: str) -> dict:
    """Non-secret facts about the local server for the result files (file names only, no directory paths)."""
    u = urlparse(_check_local(endpoint))
    root = f"{u.scheme}://{u.netloc}"
    info: dict = {}
    try:
        props = _local_request(root + "/props", "GET", None, 10)
        info["build_info"] = props.get("build_info")
        info["model_file"] = Path(str(props.get("model_path") or "")).name or None
    except Exception as e:
        info["props_error"] = f"{type(e).__name__}: {str(e)[:120]}"
    try:
        models = _local_request(root + "/v1/models", "GET", None, 10)
        info["served_models"] = [m.get("id") for m in models.get("data", [])]
    except Exception as e:
        info["models_error"] = f"{type(e).__name__}: {str(e)[:120]}"
    return info


def chat(messages: list, model: str, *, reasoning_effort: str | None = None, timeout_s: float = 120.0,
         tools: list | None = None, tool_choice: str | dict | None = None, endpoint: str | None = None) -> dict:
    if endpoint is not None:
        return _local_chat(endpoint, messages, model, reasoning_effort, timeout_s, tools, tool_choice)
    payload: dict = {"model": model, "messages": messages}
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort
    if tools is not None:
        payload["tools"] = tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    return _request("POST", "/chat/completions", payload, timeout_s, provider_of(model))


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
    elif cmd == "keycheck":
        prov = sys.argv[2] if len(sys.argv) > 2 else "meta"
        k = _key(prov)
        kp = _key_path(prov)
        print(f"key file ok: {kp} (mode {oct(kp.stat().st_mode & 0o777)}, {len(k)} characters)")
    elif cmd == "toolprobe":
        if len(sys.argv) < 3:
            sys.exit("usage: python -m patchpilot.meta_client toolprobe <model>")
        sys.exit(toolprobe(sys.argv[2]))
    else:
        sys.exit("usage: python -m patchpilot.meta_client [models | ping <model> | keycheck [meta|baseten] | toolprobe <model>]")
