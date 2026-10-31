"""Offline checks for `patchpilot.propose` with scripted model replies (no model, no key, no network).

    python -m patchpilot.propose_test
"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
from pathlib import Path

from patchpilot import discover, meta_client, propose, scan

passed = 0
REPO = Path(__file__).resolve().parent.parent
SHOP = REPO / "examples" / "shop" / "orders"


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed
    assert cond, f"{name}: {detail}"
    passed += 1
    print(f"ok  {name}")


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = propose.main(argv)
    return rc, buf.getvalue()


def reply(text: str, tokens: int = 100):
    return {"choices": [{"message": {"content": text}}], "usage": {"total_tokens": tokens}}


P = [{"name": "rows", "annotation": None, "default": None, "has_default": False},
     {"name": "limit", "annotation": None, "default": 5, "has_default": True}]

# the pieces: JSON extraction and validation
check("a bare JSON list is read", propose.extract_json('[{"a": 1}]') == [{"a": 1}])
check("a JSON list inside a code fence and prose is read", propose.extract_json('Here you go:\n```json\n[{"a": 1}]\n```\nDone') == [{"a": 1}])
check("a JSON list inside prose without a fence is read", propose.extract_json('Sure: [{"a": 1}, {"a": 2}] hope it helps') == [{"a": 1}, {"a": 2}])
check("a reply without JSON gives None", propose.extract_json("I cannot do that") is None)
ok, why = propose.validate([{"rows": [1]}, {"rows": [2], "limit": 3}], P)
check("a reply that names the parameters is accepted (a parameter with a default may be left out)", ok is not None and len(ok) == 2, why)
check("an unknown parameter name is refused", propose.validate([{"rows": 1, "x": 2}, {"rows": 3}], P)[0] is None)
check("a missing parameter without a default is refused", "missing" in propose.validate([{"limit": 1}, {"limit": 2}], P)[1])
check("equal inputs count once, and one input is not enough", propose.validate([{"rows": 1}, {"rows": 1}], P)[0] is None)
check("NaN is refused", propose.validate([{"rows": float("nan")}, {"rows": 1}], P)[0] is None)
check("the reply must be a list of objects", propose.validate("text", P)[0] is None and propose.validate([1, 2], P)[0] is None)
check("an object with a list called inputs is accepted", propose.validate({"inputs": [{"rows": 1}, {"rows": 2}]}, P)[0] is not None)
check("at most eight inputs are kept", len(propose.validate([{"rows": i} for i in range(20)], P)[0]) == 8)

with tempfile.TemporaryDirectory() as t:
    tmp = Path(t)
    src = tmp / "src"
    (src / "orders").mkdir(parents=True)
    for name in ("flag_big_orders", "fill_missing_region"):
        shutil.copy(SHOP / f"{name}.py", src / "orders" / f"{name}.py")
    out = tmp / "out"
    out.mkdir()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = discover.main([str(src), "--manifest", str(out / "scan.json"), "--probes-dir", str(out / "probes")])
    check("discover wrote a draft with two placeholder targets", rc == 0 and len(json.loads((out / "scan.json").read_text())["targets"]) == 2)
    mp = out / "scan.json"
    names = [x["function"] for x in json.loads(mp.read_text())["targets"]]
    seen_msgs: dict[str, list] = {}
    seen_kw: list = []
    FLAG_OK = ('```json\n[{"rows": [{"amount": 10}, {"amount": 120}, {"amount": 75}], "limit": 50},'
               ' {"rows": [{"amount": 5}, {"amount": 6}], "limit": 50}, {"rows": [{"amount": 500}, {"amount": 30}], "limit": 99.5}]\n```')

    def fake(messages, model, **kw):
        seen_kw.append((model, kw.get("endpoint"), kw.get("reasoning_effort")))
        fn = "flag_big_orders" if "def flag_big_orders" in messages[1]["content"] else "fill_missing_region"
        seen_msgs.setdefault(fn, []).append([m["content"] for m in messages])
        step = len(seen_msgs[fn])
        if fn == "flag_big_orders":
            return reply("I would rather explain first." if step == 1 else FLAG_OK, 50 * step)
        if step == 1:
            return reply('[{"rows": 5}, {"rows": 6}]', 30)  # a number is not a table of rows: the old library raises
        return reply('[{"data": [1]}, {"data": [2]}]', 30)  # wrong parameter names

    orig = meta_client.chat
    meta_client.chat = fake
    try:
        rc, text = run([str(mp), "--endpoint", "http://127.0.0.1:8080/v1"])
    finally:
        meta_client.chat = orig
    doc = json.loads(mp.read_text())
    by = {x["function"]: x for x in doc["targets"]}
    check("exit code 1 when one function gets no valid inputs", rc == 1, text)
    check("the function that got valid inputs lost its mark and says who proposed them",
          "placeholder" not in by["flag_big_orders"] and by["flag_big_orders"]["inputs_source"] == "proposed by muse-glimmer", str(by["flag_big_orders"]))
    check("the function that got none keeps its mark and its placeholder file",
          by["fill_missing_region"].get("placeholder") is True and json.loads((out / by["fill_missing_region"]["inputs"]).read_text()) == [{"rows": None}])
    check("the proposed inputs were written to the input file", len(json.loads((out / by["flag_big_orders"]["inputs"]).read_text())) == 3)
    st, detail, _ = scan.triage(out / by["flag_big_orders"]["file"], "flag_big_orders", out / by["flag_big_orders"]["inputs"], *scan.interpreters(out, by["flag_big_orders"]), None)
    check("scan classifies the function with the proposed inputs: silent", st == "silent", detail)
    check("the text names the tokens and the model and says what healthy means",
          "tokens" in text and "muse-glimmer" in text and "these inputs only" in text and "placeholder kept" in text, text)
    check("the local endpoint and the effort were passed to the model call", all(k == ("muse-glimmer", "http://127.0.0.1:8080/v1", "low") for k in seen_kw), str(seen_kw))
    first = seen_msgs["flag_big_orders"][0]
    check("the model gets the source of the function and no result of any run",
          "def flag_big_orders" in first[1] and not any(w in first[1].lower() for w in ("silent", "pandas 3", "differs", "healthy")), first[1])
    second = seen_msgs["flag_big_orders"][1]
    check("a reply that is not JSON is answered with the reason and a second try", len(second) == 4 and "must be a non-empty JSON list" in second[3], str(second[3:]))
    third = seen_msgs["fill_missing_region"][1]
    check("a reply that fails on the old library is answered with its error",
          "raises" in third[-1] and "old library" in third[-1], third[-1])
    check("there were exactly two tries per function", len(seen_msgs["flag_big_orders"]) == 2 and len(seen_msgs["fill_missing_region"]) == 2)

    # nothing left to do, and the guards
    rc, text = run([str(mp), "--only", "0", "--n", "9"])
    check("--n above eight is refused", rc == 2)
    meta_client.chat = lambda *a, **k: (_ for _ in ()).throw(AssertionError("no model call expected"))
    try:
        mp2 = out / "done.json"
        mp2.write_text(json.dumps({"targets": [{k: v for k, v in by["flag_big_orders"].items()}]}))
        rc, text = run([str(mp2)])
        check("a manifest without placeholder marks makes no model call", rc == 0 and "no target is marked" in text, text)
        check("a file that is not a manifest is refused", run([str(out / "d.json")])[0] == 2 and run([str(mp), "--only", "x"])[0] == 2 and run([str(mp), "--tries", "0"])[0] == 2)
    finally:
        meta_client.chat = orig

    # a hosted model with no key file: the error is reported and nothing is written
    saved = (meta_client.KEY_PATH, meta_client.BASETEN_KEY_PATH, meta_client.FIREWORKS_KEY_PATH)
    meta_client.KEY_PATH = tmp / "nokey"
    try:
        before = mp.read_text()
        rc, text = run([str(mp), "--model", "muse-spark-1.3"])
        check("a hosted model without a key file gives exit code 2 and changes nothing", rc == 2 and "Key file not found" in text and mp.read_text() == before, text)
    finally:
        meta_client.KEY_PATH = saved[0]

print(f"propose_test: {passed} checks passed")
