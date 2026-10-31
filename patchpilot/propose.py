"""Let a model propose the inputs for the placeholder targets of a draft manifest (see `patchpilot.discover`).

    python -m patchpilot.propose scan.json [--endpoint http://127.0.0.1:8080/v1 | --model muse-spark-1.3] [--n 4] [--tries 2] [--only 0,2]

For every target marked `"placeholder": true` the model gets the source of that function (and nothing else: no result from
any run) and replies with a JSON list of inputs. The reply is only data: it is parsed as JSON, never executed. Each reply is
checked by running the function with it on the OLD library (the same triage `scan` uses): it must run without an error and give
the same output twice. A reply that fails is sent back once more with the error of the old library; a target that gets no valid
inputs keeps its placeholder. The old and the new library then classify the function as `scan` does; the model does not decide.
A target with valid inputs gets them written to its input file, loses the `placeholder` mark and gets `inputs_source`.

What a result means: `silent`, `loud` or `healthy` is about THESE inputs only. `healthy` is not a proof of safety; a model may
not pick the inputs that separate the libraries. The source of the function is sent to the model you choose (a hosted one, or a
local one with --endpoint, which sends nothing off your computer). Exit code 0: every placeholder got inputs; 1: at least one did not;
2: manifest or setup problem. Standard library only.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import tempfile
from pathlib import Path

from patchpilot import meta_client, scan

MAX_INPUTS = 8
MAX_BYTES = 40_000

SYSTEM = (
    "You write test inputs for one Python function. Reply with JSON only (no prose): a list of {n} different objects, each mapping "
    "every parameter name of the function to a value. The function is called as fn(**input). Rules: values must be plain JSON "
    "(null, booleans, numbers, strings, lists, objects); a pandas DataFrame argument is written as {{\"$df\": {{\"column\": [values]}}}} "
    "and a pandas Series as {{\"$series\": {{\"values\": [..], \"index\": [..]}}}} (add \"datetime_index\": true when the index holds "
    "timestamps as strings); use small inputs (3 to 8 rows). Cover what the code handles: missing values (null), text and numbers, "
    "timestamps as strings like \"2024-03-10 08:30:00\", values on both sides of any threshold, and each branch of the code. "
    "The inputs must run without raising an error."
)


def function_source(path: Path, fn: str) -> str | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == fn:
            return ast.get_source_segment(text, n)
    return None


def extract_json(text: str):
    """The first JSON value in a reply (plain, or inside a code fence); None when there is none."""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    for chunk in ([m.group(1)] if m else []) + [text]:
        chunk = chunk.strip()
        try:
            return json.loads(chunk)
        except ValueError:
            pass
        start = min((i for i in (chunk.find("["), chunk.find("{")) if i >= 0), default=-1)
        if start >= 0:
            try:
                value, _ = json.JSONDecoder().raw_decode(chunk[start:])
                return value
            except ValueError:
                pass
    return None


def validate(value, params: list[dict], limit: int = MAX_INPUTS) -> tuple[list[dict] | None, str]:
    """(inputs, '') or (None, why). Names must match the parameters; every parameter without a default must be given."""
    if isinstance(value, dict) and isinstance(value.get("inputs"), list):
        value = value["inputs"]
    if not isinstance(value, list) or not value or not all(isinstance(x, dict) for x in value):
        return None, "the reply must be a non-empty JSON list of objects"
    names = {p["name"] for p in params}
    required = {p["name"] for p in params if not p["has_default"]}
    out, seen = [], set()
    for x in value:
        if not set(x) <= names:
            return None, f"unknown parameter name(s): {sorted(set(x) - names)}; the parameters are {sorted(names)}"
        if not required <= set(x):
            return None, f"missing parameter(s): {sorted(required - set(x))}"
        try:
            text = json.dumps(x, sort_keys=True, allow_nan=False)
        except (TypeError, ValueError):
            return None, "values must be plain JSON (no NaN or infinity)"
        if len(text) > MAX_BYTES:
            return None, "an input is too large"
        if text not in seen:
            seen.add(text)
            out.append(x)
    if len(out) < 2:
        return None, "give at least two different inputs"
    return out[:limit], ""


def propose_one(base: Path, t: dict, params: list[dict], a, chat=None) -> dict:
    """Ask for inputs for one target. Returns {"ok", "inputs", "status", "detail", "tokens", "tries"}."""
    chat = chat or meta_client.chat
    src = base / t["file"]
    code = function_source(src, t["function"])
    if code is None:
        return {"ok": False, "detail": "function not found", "tokens": 0, "tries": 0}
    old, new = scan.interpreters(base, t)
    if not old or not new or not Path(old).exists() or not Path(new).exists():
        return {"ok": False, "detail": f"no usable interpreters for {t['lib']}", "tokens": 0, "tries": 0, "setup": True}
    desc = ", ".join(f"{p['name']}" + (f": {p['annotation']}" if p["annotation"] else "") + (f" = {p['default']!r}" if p["has_default"] and p["default"] is not None else "")
                     for p in params)
    messages = [{"role": "system", "content": SYSTEM.format(n=a.n)},
                {"role": "user", "content": f"Function `{t['function']}({desc})`:\n\n```python\n{code}\n```"}]
    tokens, why = 0, ""
    for attempt in range(1, a.tries + 1):
        resp = chat(messages, a.model, reasoning_effort=a.effort, timeout_s=900 if a.endpoint else 240, endpoint=a.endpoint)
        tokens += (resp.get("usage") or {}).get("total_tokens") or 0
        reply = meta_client.text_of(resp)
        inputs, why = validate(extract_json(reply), params)
        if inputs is not None:
            with tempfile.TemporaryDirectory() as d:
                pf = Path(d) / "inputs.json"
                pf.write_text(json.dumps(inputs))
                status, detail, _ = scan.triage(src, t["function"], pf, old, new, scan.root_of(base, t))
            if status != "invalid":
                return {"ok": True, "inputs": inputs, "status": status, "detail": detail, "tokens": tokens, "tries": attempt}
            why = detail
        messages += [{"role": "assistant", "content": reply},
                     {"role": "user", "content": f"Those inputs were not usable: {why}. Reply again with corrected JSON only."}]
    return {"ok": False, "detail": f"no valid inputs after {a.tries} tr{'y' if a.tries == 1 else 'ies'}: {why}", "tokens": tokens, "tries": a.tries}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("manifest")
    ap.add_argument("--model", help="model name (default: muse-glimmer with --endpoint, otherwise muse-spark-1.3)")
    ap.add_argument("--endpoint", help="base URL of a local OpenAI-compatible server (loopback only, no API key is sent)")
    ap.add_argument("--effort", default="low", choices=["minimal", "low", "medium", "high"])
    ap.add_argument("--n", type=int, default=4, help="inputs to ask for (2 to 8, default 4)")
    ap.add_argument("--tries", type=int, default=2, help="replies to ask for per function (1 to 4, default 2)")
    ap.add_argument("--only", help="positions of the targets to fill, like 0,2")
    a = ap.parse_args(argv)
    if not 2 <= a.n <= MAX_INPUTS or not 1 <= a.tries <= 4:
        print("propose: --n must be 2 to 8 and --tries 1 to 4", file=sys.stderr)
        return 2
    a.model = a.model or ("muse-glimmer" if a.endpoint else "muse-spark-1.3")
    only = None
    if a.only is not None:
        try:
            only = {int(x) for x in a.only.split(",")}
        except ValueError:
            print("propose: --only wants positions like 0,2", file=sys.stderr)
            return 2
    mp = Path(a.manifest)
    try:
        doc = json.loads(mp.read_text())
        targets = doc["targets"]
        assert isinstance(targets, list) and targets
    except (OSError, ValueError, KeyError, AssertionError):
        print(f"propose: {mp} is not a scan manifest", file=sys.stderr)
        return 2
    base = mp.resolve().parent
    todo = [k for k, t in enumerate(targets) if isinstance(t, dict) and t.get("placeholder") is True and (only is None or k in only)]
    if not todo:
        print("propose: no target is marked as a placeholder (discover writes that mark)")
        return 0
    # the parameters come from the source again, so that a manifest written by hand works as well
    from patchpilot import discover
    failed, total_tokens = 0, 0
    for k in todo:
        t = targets[k]
        src = base / t["file"]
        params = None
        try:
            tree = ast.parse(src.read_text(encoding="utf-8", errors="replace"))
            fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == t["function"]), None)
            params = discover.parameters(fn) if fn is not None else None
        except (OSError, SyntaxError, ValueError):
            pass
        if params is None:
            print(f"[{k + 1}/{len(targets)}] {t['file']}:{t['function']}  function not found")
            failed += 1
            continue
        try:
            r = propose_one(base, t, params, a)
        except meta_client.MetaAuthError as e:
            print(f"propose: {e}", file=sys.stderr)
            return 2
        except meta_client.MetaAPIError as e:
            print(f"[{k + 1}/{len(targets)}] {t['file']}:{t['function']}  model call failed: {e}")
            failed += 1
            continue
        if r.get("setup"):
            print(f"propose: {r['detail']} (build the pinned ones with scripts/setup_envs.sh, or give the target its own \"old\" and \"new\")", file=sys.stderr)
            return 2
        total_tokens += r["tokens"]
        if not r["ok"]:
            print(f"[{k + 1}/{len(targets)}] {t['file']}:{t['function']}  {r['detail']}  ({r['tokens']} tokens); placeholder kept")
            failed += 1
            continue
        (base / t["inputs"]).write_text(json.dumps(r["inputs"], indent=1) + "\n")
        t.pop("placeholder", None)
        t["inputs_source"] = f"proposed by {a.model}"
        mp.write_text(json.dumps(doc, indent=1) + "\n")  # saved after every target, so an interruption loses nothing
        print(f"[{k + 1}/{len(targets)}] {t['file']}:{t['function']}  {len(r['inputs'])} inputs, {r['status']}: {r['detail']}  ({r['tokens']} tokens, {r['tries']} repl{'y' if r['tries'] == 1 else 'ies'})")
    print(f"{len(todo) - failed} of {len(todo)} target(s) got inputs, {total_tokens} tokens; the inputs were proposed by {a.model}")
    print("healthy or silent applies to these inputs only; a model may miss the inputs that separate the libraries. Run `scan` next.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
