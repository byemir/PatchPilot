"""Generator v2 checks (no model call): aligned lists, date-aware strings, version switch, and one re-score of a recorded patch.

    python -m patchpilot.gen2_test
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from patchpilot import differential
from patchpilot.differential import DATE_RE, generate

passed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed
    assert cond, f"{name}: {detail}"
    passed += 1
    print(f"ok  {name}")


seeds = [{"t": ["2024-01-01 00:00:00", "2024-01-01 01:00:00", "2024-01-02 00:00:00"], "c": [1.0, 2.0, 3.0], "v": [10, 20, 30]}]
g2 = generate(seeds, n=300, seed=0, v2=True)
g1 = generate(seeds, n=300, seed=0)
tbl = [x["probe"] for x in g2 if isinstance(x["probe"], dict) and all(k in x["probe"] for k in "tcv")]
check("v2: columns of one table keep the same length", tbl and all(len({len(p[k]) for k in "tcv"}) == 1 for p in tbl))
check("v1 (default) still lets columns drift apart",
      any(len({len(p[k]) for k in "tcv"}) > 1 for p in (x["probe"] for x in g1 if isinstance(x["probe"], dict) and all(k in x["probe"] for k in "tcv"))))
dates = [s for p in tbl for s in p["t"]]
check("v2: every date string stays a valid date", dates and all(DATE_RE.match(s) for s in dates), str([s for s in dates if not DATE_RE.match(s)][:3]))
check("v2: fractional seconds of 3, 6 and 9 digits all occur",
      {len(s.split(".")[1]) for s in dates if "." in s} >= {3, 6, 9})
check("v2: deterministic for a seed", generate(seeds, n=50, seed=3, v2=True) == generate(seeds, n=50, seed=3, v2=True))

repo = Path(__file__).resolve().parents[1]
rec = json.loads((repo / "docs" / "real_cases" / "results_scoped_20261029.json").read_text())
bad = next(r for r in rec if r["case"].startswith("r2f") and "Version(" in r["patch_diff"])  # branches on the pandas version
case = repo / "benchmarks" / bad["case"]
cfg = json.loads((case / "case.json").read_text())
tmp = Path(tempfile.mkdtemp())
try:
    shutil.copy(case / "app.py", tmp / "app.py")
    (tmp / "p.diff").write_text(bad["patch_diff"])
    subprocess.run(["patch", "-s", "-p1", "-d", str(tmp), "-i", "p.diff"], check=True)
    files = {"app.py": (tmp / "app.py").read_text()}
    d1 = differential.differential(case, str(repo / cfg["old"]), str(repo / cfg["new"]), files, gen=1)
    d2 = differential.differential(case, str(repo / cfg["old"]), str(repo / cfg["new"]), files)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
check("recorded version-sniffing patch: generator 1 cannot judge it (WEAK)", d1["verdict"] == "WEAK" and d1["gen"] == 1, str(d1)[:200])
check("recorded version-sniffing patch: generator 2 (from case.json) rejects it", d2["verdict"] == "DIVERGENCE" and d2["gen"] == 2, str(d2)[:200])
print(f"gen2_test: {passed} checks passed")
