"""Offline checks for `patchpilot.suggest` with scripted model replies (no model, no key, no network).

    python -m patchpilot.suggest_test
"""
import contextlib
import io
import json
import shutil
import tempfile
from pathlib import Path

from patchpilot import meta_client, suggest

passed = 0
REPO = Path(__file__).resolve().parent.parent


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed
    assert cond, f"{name}: {detail}"
    passed += 1
    print(f"ok  {name}")


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = suggest.main(argv)
    return rc, buf.getvalue()


def reply(text, tokens=40):
    return {"choices": [{"message": {"content": text}}], "usage": {"total_tokens": tokens}}


check("a well-formed answer is parsed", suggest.parse_answer({"may_differ": True, "library": "numpy", "reason": " r "})[0] == {"may_differ": True, "library": "numpy", "reason": "r"})
check("an unknown library name is dropped", suggest.parse_answer({"may_differ": False, "library": "x", "reason": 3})[0] == {"may_differ": False, "library": None, "reason": ""})
check("an answer without true or false is refused", suggest.parse_answer({"may_differ": "yes"})[0] is None and suggest.parse_answer([1])[0] is None)

with tempfile.TemporaryDirectory() as t:
    tmp = Path(t)
    src = tmp / "src"
    (src / "m").mkdir(parents=True)
    for rel in ("metrics/summary_line.py", "metrics/discounted_price.py", "orders/flag_big_orders.py", "orders/size_buckets.py"):
        shutil.copy(REPO / "examples" / "shop" / rel, src / "m" / Path(rel).name)
    (src / "m" / "plain.py").write_text("def plain(x):\n    return x + 1\n")  # imports neither library
    (src / "m" / "shape.py").write_text("import numpy as np\n\n\nclass K:\n    def meth(self, a):\n        return np.mean(a)\n\n\ndef nargs():\n    return np.zeros(1)\n")
    found = suggest.runnable_functions(src)
    names = {(c["file"], c["function"]): c for c in found}
    check("functions with the right shape in files that import the libraries are listed, without the ones the patterns already find",
          set(f for _, f in names) == {"summary_line", "discounted_price", "size_buckets"}, str(sorted(names)))
    check("the library is taken from the imports", names[("m/summary_line.py", "summary_line")]["lib"] == "numpy" and names[("m/size_buckets.py", "size_buckets")]["lib"] == "pandas")
    check("with --include-pattern-hits the pattern functions are listed too", "flag_big_orders" in {c["function"] for c in suggest.runnable_functions(src, True)})

    seen = []

    def fake(messages, model, **kw):
        code = messages[1]["content"]
        seen.append((model, kw.get("endpoint"), kw.get("reasoning_effort"), len(messages)))
        if "def summary_line" in code:
            return reply('```json\n{"may_differ": true, "library": "numpy", "reason": "str of a numpy scalar prints np.float64(...) on NumPy 2"}\n```', 50)
        if "def discounted_price" in code:
            return reply("I think it might.", 20) if len(messages) == 2 else reply('{"may_differ": true, "library": "numpy", "reason": "float32 scalar promotion"}', 30)
        return reply('{"may_differ": false, "library": "pandas", "reason": "same on both"}', 10)

    orig = meta_client.chat
    meta_client.chat = fake
    out = tmp / "out"
    out.mkdir()
    try:
        rc, text = run([str(src), "--endpoint", "http://127.0.0.1:8080/v1", "--json", str(out / "s.json"), "--manifest", str(out / "scan.json"), "--probes-dir", str(out / "probes")])
    finally:
        meta_client.chat = orig
    check("the command succeeds and says that a suggestion is a hypothesis", rc == 0 and "hypothesis" in text and "2 suggested, 1 not" in text, text)
    check("the local model and endpoint were used", all(s[:3] == ("muse-glimmer", "http://127.0.0.1:8080/v1", "low") for s in seen), str(seen))
    check("an unusable reply is asked again once", sum(1 for s in seen if s[3] == 4) == 1 and len(seen) == 4, str(seen))
    data = json.loads((out / "s.json").read_text())
    check("the answers file holds the reasons, the tokens and no source text", len(data["answers"]) == 3 and data["tokens"] == 50 + 20 + 30 + 10 and "code" not in data["answers"][0]
          and "return" not in json.dumps(data), json.dumps(data)[:300])
    man = json.loads((out / "scan.json").read_text())
    check("the draft manifest holds the suggested functions only, with their library and the placeholder mark",
          sorted(t["function"] for t in man["targets"]) == ["discounted_price", "summary_line"] and all(t["lib"] == "numpy" and t["placeholder"] is True for t in man["targets"]), str(man))

    rc, text = run([str(src), "--json", str(out / "s.json")])
    check("an existing answers file is not overwritten", rc == 2 and "not overwriting" in text, text)
    check("a missing folder and bad options are refused", run([str(tmp / "no")])[0] == 2 and run([str(src), "--manifest", "x.json"])[0] == 2 and run([str(src), "--limit", "0"])[0] == 2)

    meta_client.chat = lambda *a, **k: reply("no json at all")
    try:
        rc, text = run([str(src), "--limit", "1"])
    finally:
        meta_client.chat = orig
    check("a model that never answers in JSON is reported, not trusted", rc == 0 and "0 suggested, 0 not, 1 without an answer" in text, text)

    saved = meta_client.KEY_PATH
    meta_client.KEY_PATH = tmp / "nokey"
    try:
        rc, text = run([str(src), "--model", "muse-spark-1.3", "--limit", "1"])
    finally:
        meta_client.KEY_PATH = saved
    check("a hosted model without a key file gives exit code 2", rc == 2 and "Key file not found" in text, text)

print(f"suggest_test: {passed} checks passed")
