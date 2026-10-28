"""Run every benchmark case N times and summarize success rate, attempts and tokens."""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from patchpilot import agent, differential, sandbox

DIFF_N = 200
DIFF_SEED = 0
SCORE_KEYS = ("verdict", "generated", "valid", "core_divergences", "wide_divergences")


def score(case_dir: Path, cfg: dict, r: dict, seed: int) -> dict:
    """Run the differential on the accepted patch outside the repair loop; the model never sees this."""
    try:
        rec = json.loads((Path(r["run_dir"]) / f"attempt_{r['attempts']}.json").read_text())
        d = differential.differential(case_dir, cfg["old"], cfg["new"], rec["files"], n=DIFF_N, seed=seed)
        return {k: d.get(k) for k in SCORE_KEYS} | {"seed": seed, "examples": [e for e in d.get("examples", []) if e.get("tier") == "core"][:3]}
    except sandbox.SandboxUnavailable:
        raise
    except Exception as e:
        return {"verdict": "SCORE_ERROR", "reason": f"{type(e).__name__}: {e}"[:300], "seed": seed}


def main() -> None:
    sandbox.ensure_clean_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="muse-spark-1.3")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--token-budget", type=int, default=60000)
    ap.add_argument("--no-differential", action="store_true",
                    help="do not use the differential as an accept/reject gate inside the repair loop")
    ap.add_argument("--score-seed", type=int, default=None,
                    help="after a run is accepted, score its patch with the differential at this seed (not shown to the model)")
    ap.add_argument("--no-fs-deny", action="store_true",
                    help="run model code without OS file-system isolation (unsafe; results are marked and not counted)")
    ap.add_argument("--tools", action="store_true",
                    help="let the model call run_tests and run_probe (a tool conversation per attempt)")
    ap.add_argument("--cases", nargs="*", help="case folder names (default: all with case.json)")
    a = ap.parse_args()
    sandbox.set_fs_deny(not a.no_fs_deny)

    config = {"max_attempts": a.max_attempts, "token_budget": a.token_budget,
              "diff_check": not a.no_differential, "diff_n": DIFF_N, "diff_seed": DIFF_SEED,
              "score_seed": a.score_seed, "fs_deny": not a.no_fs_deny, "tools": a.tools}
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
                    diff_check=not a.no_differential, diff_n=DIFF_N, diff_seed=DIFF_SEED,
                    tools=a.tools,
                )
            except Exception as e:  # API or network errors count as failures but are recorded
                r = {"success": False, "reason": f"{type(e).__name__}: {e}"[:300]}
                if isinstance(e, sandbox.SandboxUnavailable):
                    raise SystemExit(f"Aborting, nothing saved: {e}")
                if isinstance(e, agent.meta_client.MetaAPIError) and any(
                        k in str(e) for k in ("HTTP 401", "HTTP 403", "Key file")):
                    raise SystemExit(f"Aborting, nothing saved: {e}")
            r.pop("diff", None)
            r["fs_deny"] = sandbox.FS_DENY
            if r.get("success") and a.score_seed is not None:
                r["scored"] = score(root / name, cfg, r, a.score_seed)
            results.append(r)
            if not r.get("success"):
                print("   reason:", str(r.get("reason"))[:200], flush=True)
            print(f"{name} run {i + 1}/{a.repeats}: success={r.get('success')} "
                  f"attempts={r.get('attempts')} tokens={r.get('tokens_used')} "
                  f"scored={r.get('scored', {}).get('verdict')}", flush=True)
        ok = [r for r in results if r.get("success")]
        row = {
            "case": name, "model": a.model, "effort": a.effort, "runs": len(results),
            "successes": len(ok),
            "first_try": sum(1 for r in ok if r.get("attempts") == 1),
            "avg_tokens": round(statistics.mean(r.get("tokens_used", 0) for r in results)),
            "config": config,
            "counted": not a.no_fs_deny,
            "results": results,
        }
        if a.score_seed is not None:
            row["scored_pass"] = sum(1 for r in ok if r.get("scored", {}).get("verdict") in ("PASS", "WEAK"))
        rows.append(row)

    Path("results").mkdir(exist_ok=True)
    out = Path("results") / f"bench_{started}_{a.model}{'_NOFSDENY' if a.no_fs_deny else ''}{'_tools' if a.tools else ''}.json"
    out.write_text(json.dumps(rows, indent=2))
    print("\n| case | runs | solved | first try | avg tokens | scored pass |\n|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['case']} | {r['runs']} | {r['successes']} | {r['first_try']} | {r['avg_tokens']} | {r.get('scored_pass', '-')} |")
    print(f"\nsaved {out}")


if __name__ == "__main__":
    main()
