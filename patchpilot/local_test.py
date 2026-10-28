"""Offline test of the local endpoint mode: a fake server on the loopback interface stands in for llama-server.
No model and no network beyond loopback; model code still runs in the sandbox.

    python -m patchpilot.local_test
"""
from __future__ import annotations

import json
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from patchpilot import agent, meta_client, sandbox

CASE = Path("benchmarks/n6_uint8_scaling")
FAILS: list = []
SEEN: list = []


def check(label, ok, detail=""):
    print(("ok:   " if ok else "FAIL: ") + label + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(label)


def make_handler(reply_content):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/props":
                self._send({"build_info": "b1-fake", "model_path": "/some/private/dir/model.gguf"})
            elif self.path == "/v1/models":
                self._send({"data": [{"id": "muse-glimmer"}]})
            elif self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "http://example.com/")
                self.send_header("Content-Length", "0")
                self.end_headers()
            else:
                self._send({"error": "not found"}, 404)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n))
            SEEN.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body})
            self._send({"choices": [{"finish_reason": "stop", "message": {
                            "role": "assistant", "content": reply_content, "reasoning_content": "fake thinking"}}],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}})

    return H


def main() -> int:
    sandbox.ensure_clean_env()
    cfg = json.loads((CASE / "case.json").read_text())
    good = json.loads((CASE / "known_good.json").read_text())["files"]
    meta_client.KEY_PATH = Path("/nonexistent/pp_key")  # the local mode must never read the key file
    srv = HTTPServer(("127.0.0.1", 0), make_handler(json.dumps({"diagnosis": "fake", "files": good})))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    root = f"http://127.0.0.1:{srv.server_address[1]}"
    base = root + "/v1"
    msgs = [{"role": "user", "content": "hi"}]

    print("== loopback only")
    for url in ("http://example.com/v1", "http://10.0.0.5:8080/v1", "http://127.0.0.1.evil.com:8080/v1",
                "https://127.0.0.1:8080/v1"):
        try:
            meta_client.chat(msgs, "muse-glimmer", endpoint=url)
            check(f"refused: {url}", False, "no exception")
        except meta_client.MetaAPIError:
            check(f"refused: {url}", True)
    check("no request left the process for the refused URLs", len(SEEN) == 0)

    print("== request shape")
    r = meta_client.chat(msgs, "muse-glimmer", reasoning_effort="low", endpoint=base)
    req = SEEN[-1]
    b = req["body"]
    check("path is /v1/chat/completions", req["path"] == "/v1/chat/completions", req["path"])
    check("published sampling values are sent", (b.get("temperature"), b.get("top_p"), b.get("top_k")) == (1.0, 0.95, 64), str(b))
    check("a hard max_tokens cap is sent", b.get("max_tokens") == meta_client.LOCAL_MAX_TOKENS, str(b))
    check("reasoning level goes through chat_template_kwargs",
          b.get("chat_template_kwargs") == {"reasoning_strength": "low"} and "reasoning_effort" not in b, str(b))
    check("no Authorization header; the key file is not needed", "authorization" not in req["headers"], str(req["headers"]))
    check("reply is read as usual", meta_client.text_of(r).startswith("{"))
    try:
        meta_client.chat(msgs, "muse-glimmer", reasoning_effort="minimal", endpoint=base)
        check("unknown reasoning level rejected", False, "no exception")
    except ValueError:
        check("unknown reasoning level rejected", True)
    info = meta_client.local_server_info(base)
    check("server info has the build and the file name only",
          info.get("build_info") == "b1-fake" and info.get("model_file") == "model.gguf"
          and info.get("served_models") == ["muse-glimmer"] and "/some/private" not in json.dumps(info), str(info))
    try:
        meta_client._local_request(root + "/redirect", "GET", None, 5)
        check("redirects are not followed", False, "no exception")
    except meta_client.MetaAPIError as e:
        check("redirects are not followed", "302" in str(e), str(e)[:100])

    print("== agent.repair with the local endpoint")
    timeouts: list = []
    orig = meta_client._local_request

    def spy(url, method, payload, timeout_s):
        if method == "POST":
            timeouts.append(timeout_s)
        return orig(url, method, payload, timeout_s)

    meta_client._local_request = spy
    n_before = len(SEEN)
    res = agent.repair(CASE, cfg["old"], cfg["new"], lib=cfg["lib"], model="muse-glimmer", effort="low",
                       runs_root=tempfile.mkdtemp(), endpoint=base)
    rec = json.loads((Path(res["run_dir"]) / "attempt_1.json").read_text())
    check("accepted through the full gate", bool(res.get("success")) and res.get("attempts") == 1, str(res)[:200])
    check("one chat request with a 900 s timeout", len(SEEN) - n_before == 1 and timeouts == [900], str(timeouts))
    check("record carries model, endpoint and sandbox flag",
          rec.get("model") == "muse-glimmer" and rec.get("endpoint") == base and rec.get("fs_deny") is True,
          str({k: rec.get(k) for k in ("model", "endpoint", "fs_deny")}))
    try:
        agent.repair(CASE, cfg["old"], cfg["new"], lib=cfg["lib"], runs_root=tempfile.mkdtemp(), endpoint=base, tools=True)
        check("tools mode with a local endpoint rejected", False, "no exception")
    except ValueError:
        check("tools mode with a local endpoint rejected", True)
    meta_client._local_request = orig
    srv.shutdown()

    print("\n" + ("all checks passed" if not FAILS else f"{len(FAILS)} check(s) failed: {FAILS}"))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
