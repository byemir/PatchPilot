"""Offline check of capture (no model, no network). Run: python -m patchpilot.capture_test"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

from patchpilot import capture, repair, scan

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
        rc = capture.main(argv)
    return rc, buf.getvalue()


with tempfile.TemporaryDirectory() as t:
    tmp = Path(t)
    (tmp / "mod.py").write_text("def total(rows, limit=5):\n    return sum(r for r in rows if r < limit)\n\n"
                                "def never(x):\n    return x\n\ndef wild(*args):\n    return args\n")
    (tmp / "go.py").write_text(
        "import mod\n"
        "mod.total([1, 2, 9], 5)\n"
        "mod.total([1, 2, 9], 5)\n"            # an equal call is kept once
        "mod.total(rows=[3, 4], limit=4)\n"     # keyword call, same shape of probe
        "mod.total([1, 2])\n"                   # default argument is recorded as well
        "mod.total((1, 2), 3)\n"                # a tuple does not survive JSON: skipped
        "mod.total([float('nan')], 3)\n"        # nan is not valid JSON: skipped
        "for i in range(30): mod.total([i], 100)\n"
        "mod.wild(1, 2)\n")
    (tmp / "test_mod.py").write_text("import unittest, mod\n\nclass T(unittest.TestCase):\n    def test_a(self):\n"
                                     "        self.assertEqual(mod.total([1], 5), 1)\n    def test_b(self):\n        self.assertEqual(mod.total([7], 5), 0)\n")
    py = sys.executable
    mf = tmp / "scan.json"
    rc, out = run(["--python", py, "--target", str(tmp / "mod.py") + ":total", "--out", str(tmp / "probes"), "--limit", "6",
                   "--manifest", str(mf), "--lib", "numpy", "--", str(tmp / "go.py")])
    probes = json.loads((tmp / "probes" / "total.json").read_text())
    check("calls with plain JSON arguments are recorded, equal ones once, tuples and nan skipped",
          rc == 0 and probes[0] == {"limit": 5, "rows": [1, 2, 9]} and {"limit": 4, "rows": [3, 4]} in probes
          and {"limit": 5, "rows": [1, 2]} in probes and all(isinstance(p["rows"], list) for p in probes) and "skipped" in out, out)
    check("at most --limit distinct calls are kept", len(probes) == 6, str(len(probes)))
    m = json.loads(mf.read_text())
    check("the manifest gets one entry with paths relative to it",
          m["targets"] == [{"file": "mod.py", "function": "total", "lib": "numpy", "inputs": "probes/total.json"}], str(m))
    run(["--python", py, "--target", str(tmp / "mod.py") + ":total", "--out", str(tmp / "probes"), "--manifest", str(mf), "--lib", "numpy", "--", str(tmp / "go.py")])
    check("running it again replaces the entry instead of adding one", len(json.loads(mf.read_text())["targets"]) == 1)

    rc, out = run(["--python", py, "--target", str(tmp / "mod.py") + ":never", "--out", str(tmp / "p2"), "--", str(tmp / "go.py")])
    check("a function that was never called records nothing and exits 1", rc == 1 and "never called" in out and not (tmp / "p2" / "never.json").exists(), out)
    rc, out = run(["--python", py, "--target", str(tmp / "mod.py") + ":wild", "--out", str(tmp / "p3"), "--", str(tmp / "go.py")])
    check("*args functions are reported as unsupported", rc == 1 and "*args" in out, out)

    rc, out = run(["--python", py, "--target", str(tmp / "mod.py") + ":total", "--out", str(tmp / "p4"), "--cwd", str(tmp), "--", "-m", "unittest", "test_mod"])
    check("a module command (-m unittest) works from the project folder too",
          rc == 0 and json.loads((tmp / "p4" / "total.json").read_text()) == [{"limit": 5, "rows": [1]}, {"limit": 5, "rows": [7]}], out)
    check("a bad target is refused", run(["--python", py, "--target", "nofile.py:f", "--out", str(tmp / "p5"), "--", "x.py"])[0] == 2)
    check("--manifest needs --lib", run(["--python", py, "--target", str(tmp / "mod.py") + ":total", "--out", str(tmp / "p5"), "--manifest", "m.json", "--", "x.py"])[0] == 2)

    # end to end: record from a script on the old pandas, then check the function on both libraries
    old, new = repair.default_python("pandas", 0), repair.default_python("pandas", 1)
    if old and new and Path(old).exists() and Path(new).exists():
        shop = tmp / "shop"
        shutil.copytree(REPO / "examples" / "shop", shop)
        (shop / "use.py").write_text(f"import sys\nsys.path.insert(0, {str(shop / 'orders')!r})\nfrom flag_big_orders import flag_big_orders\n"
                                     "flag_big_orders([{'amount': 10}, {'amount': 120}, {'amount': 75}], 50)\n"
                                     "flag_big_orders([{'amount': 500}, {'amount': 30}], 99.5)\n")
        rc, out = run(["--python", old, "--target", str(shop / "orders" / "flag_big_orders.py") + ":flag_big_orders", "--out", str(shop / "captured"),
                       "--manifest", str(shop / "mine.json"), "--lib", "pandas", "--", str(shop / "use.py")])
        check("a script run on the old pandas records the inputs of a real function", rc == 0 and "2 distinct" in out, out)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc2 = scan.main([str(shop / "mine.json"), "--triage-only", "--out-dir", str(tmp / "rep")])
        rep = json.loads((tmp / "rep" / "scan_report.json").read_text())
        check("the recorded inputs go straight into a scan and the silent break is found", rc2 == 0 and rep["counts"] == {"silent": 1}, str(rep["counts"]))
    else:
        print("skip  end-to-end check (no pinned pandas interpreters; build them with scripts/setup_envs.sh)")
print(f"capture_test: {passed} checks passed")
