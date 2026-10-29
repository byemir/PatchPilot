"""One command from your function to a verified patch (no model call is made by this file itself).

    python -m patchpilot.repair my_module.py my_function --inputs probes.json --lib pandas [--apply]

Steps: build a repair case from the function (patchpilot.make_case), let the model repair it behind the three gates
(patchpilot.agent), write the accepted patch as a diff next to a JSON report, and, only with --apply, write the
accepted file over the original. Exit code 0: accepted. 1: no accepted patch (or the file changed and was not
overwritten). 2: the case could not be built (see the message above it).

Scope: one self-contained file with a top-level function, JSON-friendly arguments and results (otherwise write a small
adapter in the same file), deterministic for fixed inputs. Accepted means the patch passed the gates that were on;
read the diff before you use it.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from patchpilot import agent, make_case, sandbox

ROOT = Path(__file__).resolve().parents[1]
ENVS = {"pandas": ("pd23", "pd30"), "numpy": ("np126", "np2")}


def default_python(lib: str, side: int) -> str | None:
    if lib not in ENVS:
        return None
    return str(ROOT / ".sandboxes" / ENVS[lib][side] / "bin" / "python")


def apply_patch(path, expected_old: str, new_text: str) -> None:
    """Overwrite the file only if it still has the content the case was built from."""
    path = Path(path)
    if path.read_text() != expected_old:
        raise RuntimeError(f"{path} changed after the case was built; not overwriting it (the diff is saved)")
    tmp = path.with_name(path.name + ".patchpilot.tmp")
    tmp.write_text(new_text)
    os.replace(tmp, path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Repair one function after a library upgrade and verify the patch.")
    ap.add_argument("file", help="Python file with the function (self-contained)")
    ap.add_argument("function", help="name of the top-level function")
    ap.add_argument("--inputs", required=True, help="JSON list of objects; the function is called as fn(**probe)")
    ap.add_argument("--lib", required=True, help="library under repair, for example pandas or numpy")
    ap.add_argument("--old", help="interpreter with the OLD library (default: .sandboxes for pandas and numpy)")
    ap.add_argument("--new", help="interpreter with the NEW library")
    ap.add_argument("--hidden-inputs", help="your own held-out inputs (default: derived)")
    ap.add_argument("--model", help="default: muse-glimmer with --endpoint, otherwise muse-spark-1.3")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--endpoint", help="base URL of a local OpenAI-compatible server (loopback only, no API key)")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--token-budget", type=int, default=60000)
    ap.add_argument("--out-dir", default=".", help="where the diff and the report are written (default: here)")
    ap.add_argument("--runs-dir", default=str(ROOT / "runs"), help="where the run records are written")
    ap.add_argument("--apply", action="store_true", help="overwrite FILE with the accepted patch (default: only write the diff)")
    a = ap.parse_args(argv)

    src = Path(a.file)
    old = a.old or default_python(a.lib, 0)
    new = a.new or default_python(a.lib, 1)
    if not src.is_file():
        print(f"repair: {src} not found", file=sys.stderr)
        return 2
    if not old or not new:
        print(f"repair: no default interpreters for {a.lib}; pass --old and --new", file=sys.stderr)
        return 2
    for p in (old, new):
        if not Path(p).exists():
            print(f"repair: interpreter not found: {p} (build the sandboxes with scripts/setup_envs.sh or pass --old/--new)", file=sys.stderr)
            return 2

    original = src.read_text()
    model = a.model or ("muse-glimmer" if a.endpoint else "muse-spark-1.3")
    with tempfile.TemporaryDirectory() as tmp:
        case = Path(tmp) / "case"
        margs = ["--src", str(src), "--fn", a.function, "--inputs", a.inputs, "--old", old, "--new", new,
                 "--lib", a.lib, "--out", str(case)]
        if a.hidden_inputs:
            margs += ["--hidden-inputs", a.hidden_inputs]
        print("== 1/2  build a repair case from your function")
        try:
            make_case.main(margs)
        except SystemExit as e:
            if e.code not in (0, None):
                print("repair: the case could not be built; nothing was changed", file=sys.stderr)
                return 2
        sandbox.set_fs_deny(True)  # make_case turns it off for its own fixtures; model code always runs isolated
        print(f"\n== 2/2  repair with {model} (effort {a.effort})")
        t0 = time.time()
        res = agent.repair(case, old, new, lib=a.lib, model=model, effort=a.effort, max_attempts=a.max_attempts,
                           token_budget=a.token_budget, runs_root=a.runs_dir, endpoint=a.endpoint)
        secs = time.time() - t0
        if not res.get("success"):
            print(json.dumps({k: v for k, v in res.items() if k != "diff"}, indent=2))
            print(f"\nnot repaired after {secs:.0f} s: no patch passed the gates; {src} was not changed")
            return 1
        rec = json.loads((Path(res["run_dir"]) / f"attempt_{res['attempts']}.json").read_text())

    new_text = (rec.get("files") or {}).get("app.py")
    diff = res["diff"].replace("--- a/app.py", f"--- a/{src.name}", 1).replace("+++ b/app.py", f"+++ b/{src.name}", 1)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"{src.stem}.{a.function}.patchpilot"
    (out / f"{stem}.diff").write_text(diff)
    d = res.get("differential") or {}
    report = {"success": True, "file": str(src), "function": a.function, "lib": a.lib, "model": model, "effort": a.effort,
              "endpoint": a.endpoint, "attempts": res["attempts"], "tokens_used": res["tokens_used"],
              "seconds": round(secs, 1), "hidden_checked": res["hidden_checked"], "differential": d,
              "diagnosis": res.get("diagnosis"), "run_dir": res["run_dir"], "applied": False}
    print(f"\naccepted after {res['attempts']} attempt(s), {res['tokens_used']} tokens, {secs:.0f} s")
    print(f"gates: visible OK, hidden {'OK' if res['hidden_checked'] else 'not run'}, differential {d.get('verdict', 'off')}"
          f" ({d.get('valid')} valid of {d.get('generated')} generated inputs, {d.get('core_divergences')} divergences)")
    if d.get("verdict") == "WEAK":
        print("note: the differential check is thin for this function (fewer than 20 valid generated inputs)")
    print(f"diagnosis: {res.get('diagnosis')}\n")
    print(diff)
    code = 0
    if a.apply:
        only_app = set((rec.get("files") or {})) == {"app.py"}
        try:
            if not only_app or new_text is None:
                raise RuntimeError("the accepted patch touches more than one file; apply the diff by hand")
            apply_patch(src, original, new_text)
            report["applied"] = True
            print(f"applied: {src} was overwritten with the accepted patch")
        except RuntimeError as e:
            print(f"not applied: {e}", file=sys.stderr)
            code = 1
    else:
        print(f"not applied (no --apply). To apply: patch -p1 < {out / (stem + '.diff')} from the file's folder, or rerun with --apply")
    (out / f"{stem}.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"wrote {out / (stem + '.diff')} and {out / (stem + '.json')}")
    return code


if __name__ == "__main__":
    sandbox.ensure_clean_env()
    sys.exit(main())
