"""Generator v2 checks (no model call): aligned lists, date-aware strings, version switch, and a constructed version-branching patch.

    python -m patchpilot.gen2_test
"""
from __future__ import annotations

import json
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
case = repo / "benchmarks" / "o2_bars_epoch_seconds"
cfg = json.loads((case / "case.json").read_text())
bad = json.loads((case / "known_bad" / "branch_on_version.json").read_text())["files"]  # divides by 10**6 on pandas 3
d1 = differential.differential(case, str(repo / cfg["old"]), str(repo / cfg["new"]), bad, gen=1)
d2 = differential.differential(case, str(repo / cfg["old"]), str(repo / cfg["new"]), bad)
check("version-branching patch: generator 1 records its version and valid-probe count", d1["gen"] == 1 and d1["valid"] > 0, str(d1)[:200])
check("version-branching patch: generator 2 (from case.json) is rejected with more valid probes",
      d2["verdict"] == "DIVERGENCE" and d2["gen"] == 2 and d2["valid"] > d1["valid"], str(d2)[:200])
check("version-branching patch: generator 2 finds divergences on wide (nanosecond) inputs", d2.get("wide_divergences", 0) > 0, str(d2)[:200])
print(f"gen2_test: {passed} checks passed")
