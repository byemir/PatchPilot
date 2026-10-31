"""Offline check that a `print` in the code under test cannot break the JSON result of the case runner.

    python -m patchpilot.runner_test
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from patchpilot import make_case

passed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed
    assert cond, f"{name}: {detail}"
    passed += 1
    print(f"ok  {name}")


APP = '''import sys
print("printed while the module is imported")


def f(x, label="t"):
    print("printed inside the function:", x)
    sys.stdout.write("also written without print\\n")
    if x == 3:
        raise ValueError("three")
    return {"x": x, "label": label}
'''

for name, probes in (("plain runner", [{"x": 1}, {"x": 2, "label": "u"}, {"x": 3}]),
                     ("table runner", [{"x": 1}, {"x": {"$df": {"a": [1, 2]}}}, {"x": 3}])):
    run, _ = make_case.build_runner("f", probes)
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "app.py").write_text(APP.replace('if x == 3:', 'if x == 3 or isinstance(x, dict) and False:'))
        (d / "run_case.py").write_text(run)
        (d / "inputs.json").write_text(json.dumps(probes))
        r = subprocess.run([sys.executable, "run_case.py", "inputs.json"], cwd=d, capture_output=True, text=True, timeout=60)
        try:
            out = json.loads(r.stdout)
        except ValueError:
            out = None
        check(f"{name}: standard output is only the JSON result although the code prints", out is not None and len(out) == 3, r.stdout[:200])
        check(f"{name}: the results are the function's results and the error is recorded", "x" in out[0] and out[2] == {"error": "ValueError"}, str(out) + r.stderr[-300:])
        check(f"{name}: what the code printed went to the error stream", "printed inside the function" in r.stderr and "printed while the module is imported" in r.stderr, r.stderr[:200])

with tempfile.TemporaryDirectory() as t:
    d = Path(t)
    run, test = make_case.build_runner("f", [{"x": {"$df": {"a": [1]}}}])
    (d / "app.py").write_text(APP)
    (d / "run_case.py").write_text(run)
    (d / "test_case.py").write_text(test)
    (d / "inputs.json").write_text(json.dumps([{"x": {"$df": {"a": [1]}}}]))
    r = subprocess.run([sys.executable, "-c", "import run_case, sys; print('stdout is the real one:', sys.stdout is sys.__stdout__)"], cwd=d, capture_output=True, text=True, timeout=60)
    check("importing the table runner (as the visible test does) leaves standard output alone", "stdout is the real one: True" in r.stdout, r.stdout + r.stderr)

# a function whose name the table runner uses for itself is refused with a clear message instead of misbehaving
import contextlib
import io

for bad in ("default", "dec", "json"):
    with tempfile.TemporaryDirectory() as t:
        src = Path(t) / "m.py"
        src.write_text(f"def {bad}(x):\n    return x\n")
        buf = io.StringIO()
        try:
            with contextlib.redirect_stderr(buf):
                make_case.check_source(src, bad)
            ok = False
        except SystemExit:
            ok = "used by the case runner" in buf.getvalue()
        check(f"a function called {bad} is refused with a clear message", ok, buf.getvalue())
with tempfile.TemporaryDirectory() as t:
    src = Path(t) / "m.py"
    src.write_text("def path(x):\n    return x\n\n\ndef out(x):\n    return x\n")
    make_case.check_source(src, "path")
    make_case.check_source(src, "out")
    check("functions called path and out are fine (the plain runner no longer uses those names)", True)

# the size limit of the project copy: a module above 200 KB is left out by default and can be let in for one run
import tempfile as _tf
with _tf.TemporaryDirectory() as _d:
    _root = Path(_d) / "proj"
    (_root / "pkg").mkdir(parents=True)
    (_root / "pkg" / "small.py").write_text("x = 1\n")
    (_root / "pkg" / "big.py").write_text("y = 2\n" + "#" * 250_000 + "\n")
    _dst = Path(_d) / "dst"
    _dst.mkdir()
    make_case.copy_project(_root, _dst)
    check("a module above 200 KB is not copied by default", (_dst / "pkg" / "small.py").exists() and not (_dst / "pkg" / "big.py").exists())
    _old = make_case.MAX_FILE
    make_case.MAX_FILE = 300_000
    try:
        _dst2 = Path(_d) / "dst2"
        _dst2.mkdir()
        make_case.copy_project(_root, _dst2)
        check("with a higher limit the same module is copied", (_dst2 / "pkg" / "big.py").exists())
    finally:
        make_case.MAX_FILE = _old
    check("the limits come from the environment, never below the default and never above the cap",
          make_case._limit("PATCHPILOT_X", 200_000, 2_000_000) == 200_000)
    import os as _os
    _os.environ["PATCHPILOT_X"] = "999999999"
    check("a value above the cap is cut to the cap", make_case._limit("PATCHPILOT_X", 200_000, 2_000_000) == 2_000_000)
    _os.environ["PATCHPILOT_X"] = "5"
    check("a value below the default is raised to the default", make_case._limit("PATCHPILOT_X", 200_000, 2_000_000) == 200_000)
    _os.environ["PATCHPILOT_X"] = "abc"
    check("a value that is not a number gives the default", make_case._limit("PATCHPILOT_X", 200_000, 2_000_000) == 200_000)
    del _os.environ["PATCHPILOT_X"]

print(f"runner_test: {passed} checks passed")
