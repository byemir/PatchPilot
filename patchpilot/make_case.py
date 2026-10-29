"""Build a repair case from your own function (standard library only; no model call).

    python -m patchpilot.make_case --src my_module.py --fn my_function --inputs probes.json \\
        --old /path/to/old/python --new /path/to/new/python --lib pandas --out my_case

probes.json is a list of JSON objects. The function is called as fn(**probe) and must return JSON-friendly values
(dicts, lists, strings, numbers, booleans, null); if your function takes a DataFrame or an array, write a small
adapter function in the same file. The file must be self-contained (standard library and the library under repair)
and deterministic for fixed inputs. The golden output comes from the OLD interpreter. Held-out inputs are derived
with the differential generator and kept only if the old library reproduces them; or pass --hidden-inputs.
The result is a case folder that `python -m patchpilot.agent` can repair.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from patchpilot import check, differential, sandbox

RUN = '''import json
import sys

from app import {fn}

path = sys.argv[1] if len(sys.argv) > 1 else "inputs.json"
with open(path) as f:
    probes = json.load(f)

out = []
for probe in probes:
    try:
        out.append({fn}(**probe))
    except Exception as e:
        out.append({{"error": type(e).__name__}})
print(json.dumps(out))
'''

TEST = '''import json
from pathlib import Path

from app import {fn}


def test_runs_on_the_recorded_inputs():
    probes = json.loads((Path(__file__).resolve().parent.parent / "inputs.json").read_text())
    for probe in probes:
        json.dumps({fn}(**probe))
'''


def fail(msg: str, code: int = 1):
    print(f"make_case: {msg}", file=sys.stderr)
    sys.exit(code)


def is_error(x) -> bool:
    return isinstance(x, dict) and set(x) == {"error"}


def same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def run_probes(py, d: Path, name: str):
    r = subprocess.run([os.path.abspath(py), "run_case.py", name], cwd=d, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return None, r.stderr.strip()[-400:]
    try:
        return json.loads(r.stdout), ""
    except json.JSONDecodeError:
        return None, "the output is not JSON"


def check_source(src: Path, fn: str) -> None:
    try:
        tree = ast.parse(src.read_text())
    except SyntaxError as e:
        fail(f"{src} is not valid Python: {e}")
    if fn not in {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}:
        fail(f"no top-level function named {fn} in {src}")
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.level:
            fail("the file uses a relative import; the function must live in a self-contained file")


def derive_hidden(out: Path, inputs: list, old: str, new: str, want: int, candidates: int):
    cands = [g["probe"] for g in differential.generate(inputs, n=candidates, seed=0) if g["tier"] == "core"]
    if not cands:
        fail("the differential generator produced no candidate inputs; pass --hidden-inputs")
    (out / "cand.json").write_text(json.dumps(cands))
    r1, e1 = run_probes(old, out, "cand.json")
    r2, e2 = run_probes(old, out, "cand.json")
    if r1 is None or r2 is None:
        fail(f"the old interpreter failed on the candidate inputs: {e1 or e2}")
    keep = [i for i in range(len(cands)) if same(r1[i], r2[i]) and not is_error(r1[i])]
    if not keep:
        fail("no candidate input gave a reproducible result on the old library; pass --hidden-inputs")
    (out / "cand.json").write_text(json.dumps([cands[i] for i in keep]))
    rn, en = run_probes(new, out, "cand.json")
    (out / "cand.json").unlink()
    if rn is None:
        fail(f"the new interpreter failed on the candidate inputs: {en}")
    breaking = [i for k, i in enumerate(keep) if not same(rn[k], r1[i])]
    unchanged = [i for k, i in enumerate(keep) if same(rn[k], r1[i])]
    if not breaking:
        fail("no generated input separates the old and the new library; pass --hidden-inputs")
    n_break = min(len(breaking), max(1, (2 * want) // 3))
    chosen = breaking[:n_break] + unchanged[: max(0, want - n_break)]
    chosen += breaking[n_break : n_break + max(0, want - len(chosen))]
    return [cands[i] for i in chosen], [r1[i] for i in chosen], len(breaking), len(keep)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Build a PatchPilot repair case from your own function.")
    ap.add_argument("--src", required=True, help="Python file with the function (self-contained)")
    ap.add_argument("--fn", required=True, help="name of the top-level function")
    ap.add_argument("--inputs", required=True, help="JSON file: a list of objects, the function is called as fn(**probe)")
    ap.add_argument("--old", required=True, help="Python interpreter with the OLD library version")
    ap.add_argument("--new", required=True, help="Python interpreter with the NEW library version")
    ap.add_argument("--lib", required=True, help="library name, for example pandas or numpy")
    ap.add_argument("--out", required=True, help="case folder to create (must not exist)")
    ap.add_argument("--hidden-inputs", help="JSON file with your own held-out inputs (same shape as --inputs)")
    ap.add_argument("--hidden", type=int, default=8, help="number of derived held-out inputs (default 8)")
    ap.add_argument("--candidates", type=int, default=200, help="generated candidates to choose from (default 200)")
    a = ap.parse_args(argv)

    src, out = Path(a.src), Path(a.out)
    if not src.is_file():
        fail(f"{src} not found")
    if out.exists():
        fail(f"{out} already exists; not overwriting")
    for p in (a.old, a.new):
        if not Path(p).exists():
            fail(f"interpreter not found: {p}")
    check_source(src, a.fn)
    inputs = json.loads(Path(a.inputs).read_text())
    if not isinstance(inputs, list) or not inputs or not all(isinstance(p, dict) for p in inputs):
        fail("--inputs must be a non-empty JSON list of objects")

    try:
        (out / "tests").mkdir(parents=True)
        (out / "app.py").write_text(src.read_text())
        (out / "run_case.py").write_text(RUN.format(fn=a.fn))
        (out / "tests" / "__init__.py").write_text("")
        (out / "tests" / "test_app.py").write_text(TEST.format(fn=a.fn))
        (out / "case.json").write_text(json.dumps({"lib": a.lib, "old": os.path.abspath(a.old), "new": os.path.abspath(a.new)}) + "\n")
        (out / "inputs.json").write_text(json.dumps(inputs, indent=1) + "\n")

        g1, e1 = run_probes(a.old, out, "inputs.json")
        if g1 is None:
            fail(f"the function does not run on the old interpreter ({e1}); is the file self-contained and are the results JSON-friendly?")
        bad = [i for i, x in enumerate(g1) if is_error(x)]
        if bad:
            fail(f"the function raises on the old library for your inputs at positions {bad}; fix the inputs")
        g2, _ = run_probes(a.old, out, "inputs.json")
        if g2 is None or not same(g1, g2):
            fail("the function is not deterministic on your inputs; seed any randomness inside the function or its arguments")
        n1, e2 = run_probes(a.new, out, "inputs.json")
        if n1 is None:
            fail(f"the function crashes on the new interpreter ({e2}): that is a loud failure, not a silent one")
        differing = sum(not same(x, y) for x, y in zip(g1, n1))
        if differing == 0:
            fail("the new library gives the same output on all your inputs: nothing to repair")
        (out / "golden.json").write_text(json.dumps(g1) + "\n")

        if a.hidden_inputs:
            hidden = json.loads(Path(a.hidden_inputs).read_text())
            (out / "cand.json").write_text(json.dumps(hidden))
            h1, he = run_probes(a.old, out, "cand.json")
            h2, _ = run_probes(a.old, out, "cand.json")
            (out / "cand.json").unlink()
            if h1 is None or h2 is None or not same(h1, h2) or any(is_error(x) for x in h1):
                fail(f"your --hidden-inputs are not reproducible without errors on the old library {he}")
            hidden_gold, n_break, n_keep = h1, None, None
        else:
            hidden, hidden_gold, n_break, n_keep = derive_hidden(out, inputs, a.old, a.new, a.hidden, a.candidates)
        (out / "hidden_inputs.json").write_text(json.dumps(hidden, indent=1) + "\n")
        (out / "hidden_golden.json").write_text(json.dumps(hidden_gold) + "\n")
    except BaseException:
        shutil.rmtree(out, ignore_errors=True)
        raise

    sandbox.set_fs_deny(False)  # the fixtures are your own code; model code is isolated by the agent
    vo, vn = check.check(out, a.old), check.check(out, a.new)
    ho = check.check(out, a.old, "hidden_inputs.json", "hidden_golden.json")
    hn = check.check(out, a.new, "hidden_inputs.json", "hidden_golden.json")
    print(f"case written to {out}")
    print(f"  your inputs: the new library differs on {differing} of {len(inputs)}")
    if n_break is not None:
        print(f"  held-out inputs: {len(hidden)} chosen from {n_keep} reproducible candidates, {n_break} of which separate the libraries")
    print(f"  verdicts: visible old={vo['verdict']} new={vn['verdict']}; hidden old={ho['verdict']} new={hn['verdict']}")
    if vo["verdict"] != "OK" or vn["verdict"] != "SILENT_BREAKAGE" or ho["verdict"] != "OK":
        print("  WARNING: this is not a clean silent breakage (expected old=OK, new=SILENT_BREAKAGE, hidden old=OK); the agent will refuse it", file=sys.stderr)
        sys.exit(2)
    print("next: python -m patchpilot.agent " + f"{out} {a.old} {a.new} --lib {a.lib}")


if __name__ == "__main__":
    main()
