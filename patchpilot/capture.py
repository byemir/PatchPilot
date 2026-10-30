"""Record real inputs for a scan: run your own tests or script once on the OLD library and note the arguments of the calls.

    python -m patchpilot.capture --python OLD_PYTHON --target orders/mod.py:total --out probes \\
        --manifest scan.json --lib pandas -- -m unittest discover tests

Everything after `--` is the command: `-m MODULE ARGS...` or `SCRIPT ARGS...`. It runs with OLD_PYTHON (the interpreter that
has the old library) and your normal permissions, like any run of your own tests; it is not isolated. While it runs, every
call of a --target function (FILE:FUNCTION, a top-level function with plain named parameters) is recorded when all its
arguments are plain JSON values (null, bool, number, string, list, dict; a tuple or an object is skipped). Equal calls are
kept once, at most --limit per function. The result is one JSON list per function in --out (the call is fn(**probe)),
and, with --manifest, an entry in the scan manifest. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

BOOTSTRAP = r'''
import atexit, json, os, runpy, sys, threading
spec = json.loads(os.environ["PP_CAPTURE"]); LIMIT = spec["limit"]
by_key = {}
for t in spec["targets"]:
    by_key[(os.path.realpath(t["file"]), t["function"])] = {"probes": [], "seen": set(), "calls": 0, "skipped": 0, "unsupported": False, **t}
real = {}
def prof(frame, event, arg):
    if event != "call":
        return
    code = frame.f_code
    k = real.get(code.co_filename)
    if k is None:
        k = real[code.co_filename] = os.path.realpath(code.co_filename)
    rec = by_key.get((k, code.co_name))
    if rec is None:
        return
    rec["calls"] += 1
    if code.co_flags & 0x0C or code.co_posonlyargcount:  # *args, **kwargs or positional-only parameters
        rec["unsupported"] = True
        return
    names = code.co_varnames[: code.co_argcount + code.co_kwonlyargcount]
    try:
        probe = {n: frame.f_locals[n] for n in names}
        text = json.dumps(probe, sort_keys=True, allow_nan=False)
        if json.loads(text) != probe:  # a tuple or a subclass would not come back equal
            raise ValueError
    except Exception:
        rec["skipped"] += 1
        return
    if text in rec["seen"] or len(rec["probes"]) >= LIMIT:
        return
    rec["seen"].add(text)
    rec["probes"].append(json.loads(text))
def finish():
    sys.setprofile(None); threading.setprofile(None)
    out = {}
    for (f, n), r in by_key.items():
        out[r["key"]] = {"probes": r["probes"], "calls": r["calls"], "skipped": r["skipped"], "unsupported": r["unsupported"]}
    with open(spec["result"], "w") as fh:
        json.dump(out, fh)
atexit.register(finish)
cmd = sys.argv[1:]
sys.setprofile(prof); threading.setprofile(prof)
if cmd[0] == "-m":
    sys.argv = [cmd[1]] + cmd[2:]
    runpy.run_module(cmd[1], run_name="__main__", alter_sys=True)
else:
    sys.argv = cmd
    sys.path.insert(0, os.path.dirname(os.path.abspath(cmd[0])))  # like `python script.py`
    runpy.run_path(cmd[0], run_name="__main__")
'''


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Record call arguments of functions while your own tests or script run on the old library.",
                                 usage="python -m patchpilot.capture --python PY --target FILE:FUNC --out DIR [--manifest scan.json --lib LIB] -- COMMAND")
    ap.add_argument("--python", required=True, help="interpreter with the OLD library")
    ap.add_argument("--target", action="append", required=True, help="FILE:FUNCTION (repeatable)")
    ap.add_argument("--out", required=True, help="folder for the probe files")
    ap.add_argument("--limit", type=int, default=10, help="most distinct calls kept per function (default 10)")
    ap.add_argument("--manifest", help="scan manifest to create or update")
    ap.add_argument("--lib", help="library under repair (needed with --manifest)")
    ap.add_argument("--cwd", help="folder to run the command in (default: here)")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("command", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
    if not cmd:
        print("capture: give the command after --", file=sys.stderr)
        return 2
    if a.manifest and not a.lib:
        print("capture: --manifest needs --lib", file=sys.stderr)
        return 2
    targets = []
    for t in a.target:
        f, _, fn = t.rpartition(":")
        if not f or not fn or not Path(f).is_file():
            print(f"capture: bad target {t!r} (want FILE:FUNCTION, the file must exist)", file=sys.stderr)
            return 2
        targets.append({"key": f"{Path(f).resolve()}:{fn}", "file": str(Path(f).resolve()), "function": fn})
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    result = out / ".capture_result.json"
    env = dict(os.environ)
    env["PP_CAPTURE"] = json.dumps({"targets": targets, "limit": a.limit, "result": str(result)})
    try:
        p = subprocess.run([a.python, "-c", BOOTSTRAP, *cmd], env=env, timeout=a.timeout, cwd=a.cwd)
    except subprocess.TimeoutExpired:
        print("capture: the command ran too long", file=sys.stderr)
        return 1
    if not result.is_file():
        print("capture: the command did not finish cleanly; nothing recorded", file=sys.stderr)
        return 1
    got = json.loads(result.read_text())
    result.unlink()
    if p.returncode != 0:
        print(f"capture: the command exited with code {p.returncode}; recording what it did call", file=sys.stderr)
    entries, missing = [], 0
    for t in targets:
        r = got[t["key"]]
        name = t["function"]
        if not r["probes"]:
            why = "uses *args, **kwargs or positional-only parameters" if r["unsupported"] else (
                "was never called" if not r["calls"] else f"was called {r['calls']} times, never with plain JSON arguments")
            print(f"  {name}: nothing recorded ({why})")
            missing += 1
            continue
        pf = out / f"{name}.json"
        pf.write_text(json.dumps(r["probes"], indent=1) + "\n")
        print(f"  {name}: {len(r['probes'])} distinct call(s) recorded from {r['calls']}" + (f", {r['skipped']} skipped (not plain JSON)" if r["skipped"] else "") + f" -> {pf}")
        entries.append((t, pf))
    if a.manifest and entries:
        mp = Path(a.manifest)
        data = json.loads(mp.read_text()) if mp.is_file() else {"targets": []}
        base = mp.resolve().parent
        for t, pf in entries:
            e = {"file": os.path.relpath(t["file"], base), "function": t["function"], "lib": a.lib, "inputs": os.path.relpath(pf.resolve(), base)}
            data["targets"] = [x for x in data["targets"] if not (x.get("file") == e["file"] and x.get("function") == e["function"])] + [e]
        mp.write_text(json.dumps(data, indent=1) + "\n")
        print(f"manifest: {mp} ({len(data['targets'])} target(s))")
    return 0 if entries and not missing else 1


if __name__ == "__main__":
    sys.exit(main())
