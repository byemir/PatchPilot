"""Re-score recorded patches with the differential gate at a given generator version (no model call).

    python scripts/rescore_recorded.py docs/real_cases/results_scoped_20261029.json --out docs/real_cases/rescore_gen2_20261029.json

Every record needs "case" (a folder under benchmarks/), "run" and "patch_diff" (unified diff against that case's app.py).
Each patch is applied to a copy of app.py with the system `patch` program and judged with generator 1 and generator 2.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from patchpilot import differential  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=200)
    a = ap.parse_args()
    rows = []
    for r in json.loads(Path(a.results).read_text()):
        case = ROOT / "benchmarks" / r["case"]
        cfg = json.loads((case / "case.json").read_text())
        old, new = str(ROOT / cfg["old"]), str(ROOT / cfg["new"])
        tmp = Path(tempfile.mkdtemp())
        try:
            shutil.copy(case / "app.py", tmp / "app.py")
            (tmp / "p.diff").write_text(r["patch_diff"])
            subprocess.run(["patch", "-s", "-p1", "-d", str(tmp), "-i", "p.diff"], check=True)
            files = {"app.py": (tmp / "app.py").read_text()}
            row = {"case": r["case"], "run": r["run"], "recorded": r["differential"]}
            for g in (1, 2):
                d = differential.differential(case, old, new, files, n=a.n, seed=0, gen=g)
                row[f"gen{g}"] = {"verdict": d["verdict"], "valid": d.get("valid"), "wide_divergences": d.get("wide_divergences")}
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        rows.append(row)
        print(row["run"], row["recorded"], row["gen1"]["verdict"], "->", row["gen2"]["verdict"], flush=True)
    Path(a.out).write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main()
