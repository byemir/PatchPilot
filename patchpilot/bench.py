"""Run every benchmark case N times and summarize success rate, attempts and tokens."""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from patchpilot import agent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="muse-spark-1.3")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--token-budget", type=int, default=60000)
    ap.add_argument("--cases", nargs="*", help="case folder names (default: all with case.json)")
    a = ap.parse_args()

    root = Path("benchmarks")
    names = a.cases or sorted(p.parent.name for p in root.glob("*/case.json"))
    rows = []
    started = time.strftime("%Y%m%d-%H%M%S")
    for name in names:
        cfg = json.loads((root / name / "case.json").read_text())
        results = []
        for i in range(a.repeats):
            try:
                r = agent.repair(
                    root / name, cfg["old"], cfg["new"], lib=cfg["lib"], model=a.model,
                    effort=a.effort, max_attempts=a.max_attempts, token_budget=a.token_budget,
                )
            except Exception as e:  # API or network errors count as failures but are recorded
                r = {"success": False, "reason": f"{type(e).__name__}: {e}"[:300]}
            r.pop("diff", None)
            results.append(r)
            print(f"{name} run {i + 1}/{a.repeats}: success={r.get('success')} "
                  f"attempts={r.get('attempts')} tokens={r.get('tokens_used')}", flush=True)
        ok = [r for r in results if r.get("success")]
        rows.append({
            "case": name, "model": a.model, "effort": a.effort, "runs": len(results),
            "successes": len(ok),
            "first_try": sum(1 for r in ok if r.get("attempts") == 1),
            "avg_tokens": round(statistics.mean(r.get("tokens_used", 0) for r in results)),
            "results": results,
        })

    Path("results").mkdir(exist_ok=True)
    out = Path("results") / f"bench_{started}_{a.model}.json"
    out.write_text(json.dumps(rows, indent=2))
    print("\n| case | runs | solved | first try | avg tokens |\n|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['case']} | {r['runs']} | {r['successes']} | {r['first_try']} | {r['avg_tokens']} |")
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
