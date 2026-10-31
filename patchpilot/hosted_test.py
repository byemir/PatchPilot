"""Offline check of the hosted-model clients: each service gets its own URL and its own key, never the other's, and no redirect is
followed. No network, no real key. Run: python -m patchpilot.hosted_test"""
from __future__ import annotations

import json
import os
import tempfile
import urllib.request
from pathlib import Path

from . import meta_client as mc

passed = 0


def check(name, cond, detail=""):
    global passed
    assert cond, f"{name}: {detail}"
    passed += 1
    print(f"ok  {name}")


class FakeResp:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


seen: list[dict] = []
handlers_seen: list = []


class FakeOpener:
    def open(self, req, timeout=None):
        seen.append({"url": req.full_url, "auth": req.get_header("Authorization"), "body": json.loads(req.data.decode()) if req.data else None})
        return FakeResp(json.dumps({"choices": [{"message": {"content": "pong"}}], "usage": {}}).encode())


def fake_build_opener(*handlers):
    handlers_seen.extend(handlers)
    return FakeOpener()


def write_key(path: Path, text: str, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    path.write_text(text + "\n")
    os.chmod(path, mode)


saved = (mc.KEY_PATH, mc.BASETEN_KEY_PATH, urllib.request.build_opener)
with tempfile.TemporaryDirectory() as t:
    root = Path(t) / "cfg"
    mc.KEY_PATH = root / "meta_key"
    mc.BASETEN_KEY_PATH = root / "baseten_key"
    urllib.request.build_opener = fake_build_opener
    try:
        check("the hackathon Baseten model goes to Baseten", mc.provider_of("meta-models/muse-spark-open-1026") == "baseten")
        check("other model names go to the Meta API", mc.provider_of("muse-spark-1.3") == "meta" and mc.provider_of("meta-models/muse-spark-open") == "meta")
        check("no key file at all is reported as none", mc.any_key_file() is False)
        try:
            mc.chat([{"role": "user", "content": "x"}], "meta-models/muse-spark-open-1026")
            check("a missing Baseten key is refused", False)
        except mc.MetaAuthError as e:
            check("a missing Baseten key is refused and names its own file", "baseten_key" in str(e), str(e))
        write_key(mc.BASETEN_KEY_PATH, "BASETEN-SECRET")
        check("one key file is enough for the guards", mc.any_key_file() is True)
        try:
            mc.chat([{"role": "user", "content": "x"}], "muse-spark-1.3")
            check("the Meta call without a Meta key is refused", False)
        except mc.MetaAuthError as e:
            check("the Baseten key is never used for a Meta call", "meta_key" in str(e), str(e))
        write_key(mc.KEY_PATH, "META-SECRET")
        mc.chat([{"role": "user", "content": "x"}], "meta-models/muse-spark-open-1026", reasoning_effort="low")
        mc.chat([{"role": "user", "content": "x"}], "muse-spark-1.3", reasoning_effort="low")
        b, m = seen[-2], seen[-1]
        check("the Baseten call goes to the fixed Baseten URL with the Baseten key",
              b["url"] == "https://inference.baseten.co/v1/chat/completions" and b["auth"] == "Bearer BASETEN-SECRET", str(b["url"]))
        check("the Meta call goes to the Meta URL with the Meta key",
              m["url"] == "https://api.meta.ai/v1/chat/completions" and m["auth"] == "Bearer META-SECRET", str(m["url"]))
        check("the model name is sent as given", b["body"]["model"] == "meta-models/muse-spark-open-1026")
        check("redirects are not followed for keyed calls", any(isinstance(h, mc._NoRedirect) for h in handlers_seen))
        os.chmod(mc.BASETEN_KEY_PATH, 0o644)
        try:
            mc.chat([{"role": "user", "content": "x"}], "meta-models/muse-spark-open-1026")
            check("an open key file is refused", False)
        except mc.MetaAuthError as e:
            check("a Baseten key file with open permissions is refused", "too open" in str(e), str(e))
        os.chmod(mc.BASETEN_KEY_PATH, 0o600)
        mc.BASETEN_KEY_PATH.write_text("\n")
        try:
            mc.chat([{"role": "user", "content": "x"}], "meta-models/muse-spark-open-1026")
            check("an empty key file is refused", False)
        except mc.MetaAuthError as e:
            check("an empty Baseten key file is refused", "empty" in str(e), str(e))
        check("the key text appears in no recorded body", all("SECRET" not in json.dumps(s["body"]) for s in seen))
    finally:
        mc.KEY_PATH, mc.BASETEN_KEY_PATH, urllib.request.build_opener = saved
print(f"hosted_test: {passed} checks passed")
