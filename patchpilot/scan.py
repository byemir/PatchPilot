"""Scan a set of functions after a library upgrade, repair the silently broken ones, write one report (standard library only).

    python -m patchpilot.scan scan.json [--endpoint http://127.0.0.1:8080/v1] [--apply] [--triage-only] [--fail-on-silent]

scan.json lists the functions to check (paths are relative to the manifest):

    {"targets": [{"file": "analytics/session_span.py", "function": "span_seconds", "lib": "pandas",
                  "inputs": "probes/span_seconds.json"}, ...]}

Every target is run on the old and on the new library with its inputs. The result is one of
  healthy  - same output on both libraries for all inputs
  silent   - the output differs and nothing crashes: this one is repaired (patchpilot.make_case + patchpilot.agent)
  loud     - the new library raises for inputs the old one handled: reported, not repaired (it is not a silent break)
  invalid  - the function does not run on the old library, is not deterministic, or the file is not usable
PatchPilot does not discover functions or inputs by itself: the manifest and the inputs come from you.
Accepted means the patch passed the gates that were on; read the diffs. Files change only with --apply.
Exit code: 0 all silent targets repaired, 1 at least one silent target not repaired, 2 manifest or setup problem.
With --fail-on-silent the exit code is also 1 when a target is still silent (use it with --triage-only as a CI gate: no model, no key).
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import time
from pathlib import Path

from patchpilot import agent, make_case, repair, sandbox, view

ROOT = Path(__file__).resolve().parents[1]


def triage(src: Path, fn: str, probes_file: Path, old: str, new: str) -> tuple[str, str, dict | None]:
    """Return (status, detail, example) for one function; runs the user's code on the old and the new interpreter.
    example is the first input on which the libraries differ, with both outputs (None when there is none)."""
    try:
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            make_case.check_source(src, fn)
    except SystemExit:
        return "invalid", buf.getvalue().replace("make_case: ", "").strip(), None
    probes = json.loads(probes_file.read_text())
    if not isinstance(probes, list) or not probes or not all(isinstance(p, dict) for p in probes):
        return "invalid", "inputs must be a non-empty JSON list of objects", None
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "app.py").write_text(src.read_text())
        (d / "run_case.py").write_text(make_case.templates(fn, probes)[0].format(fn=fn))
        (d / "inputs.json").write_text(json.dumps(probes))
        g1, e1 = make_case.run_probes(old, d, "inputs.json")
        if g1 is None:
            return "invalid", f"does not run on the old library ({e1})", None
        if any(make_case.is_error(x) for x in g1):
            return "invalid", "raises on the old library for your inputs", None
        g2, _ = make_case.run_probes(old, d, "inputs.json")
        if g2 is None or not make_case.same(g1, g2):
            return "invalid", "not deterministic on your inputs", None
        n1, e2 = make_case.run_probes(new, d, "inputs.json")
        if n1 is None:
            return "loud", f"crashes on the new library ({e2})", None
        diff = [i for i, (x, y) in enumerate(zip(g1, n1)) if not make_case.same(x, y)]
        if not diff:
            return "healthy", f"same output on all {len(probes)} inputs", None
        ex = {"input": probes[diff[0]], "old": g1[diff[0]], "new": n1[diff[0]]}
        if all(make_case.is_error(n1[i]) for i in diff):
            return "loud", f"raises {n1[diff[0]]['error']} on the new library for {len(diff)} of {len(probes)} inputs", ex
        return "silent", f"the new library differs on {len(diff)} of {len(probes)} inputs and nothing is raised", ex


def repair_one(src: Path, fn: str, lib: str, probes_file: Path, old: str, new: str, o: argparse.Namespace, on_attempt=None) -> dict:
    """Build a case, let the model repair it behind the gates; returns the record for the report."""
    original = src.read_text()
    model = o.model or ("muse-glimmer" if o.endpoint else "muse-spark-1.3")
    rec: dict = {"model": model, "effort": o.effort, "endpoint": o.endpoint}
    with tempfile.TemporaryDirectory() as t:
        case = Path(t) / "case"
        buf = io.StringIO()
        margs = ["--src", str(src), "--fn", fn, "--inputs", str(probes_file), "--old", old, "--new", new,
                 "--lib", lib, "--out", str(case)]
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                make_case.main(margs)
        except SystemExit as e:
            if e.code not in (0, None):
                return {**rec, "status": "case_failed", "detail": buf.getvalue().strip().splitlines()[-1][:300]}
        except Exception as e:  # one function must not stop the whole scan
            return {**rec, "status": "case_failed", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
        sandbox.set_fs_deny(True)  # model code always runs isolated
        t0 = time.time()
        try:
            res = agent.repair(case, old, new, lib=lib, model=model, effort=o.effort, max_attempts=o.max_attempts,
                               token_budget=o.token_budget, runs_root=o.runs_dir, endpoint=o.endpoint,
                               progress=on_attempt)
        except Exception as e:  # network or server problem: report it, go on with the next target
            return {**rec, "status": "error", "detail": f"{type(e).__name__}: {str(e)[:200]}"}
        secs = round(time.time() - t0, 1)
        rec.update({"seconds": secs, "tokens": res.get("tokens_used"), "run_dir": res.get("run_dir")})
        if res.get("run_dir"):  # the gate outcome of every attempt travels with the report, so it can be read without runs/
            rec["attempts_detail"] = view.run_view(Path(res["run_dir"]))["attempts"]
        if not res.get("success"):
            return {**rec, "status": "not_repaired", "detail": res.get("reason")}
        last = json.loads((Path(res["run_dir"]) / f"attempt_{res['attempts']}.json").read_text())
    new_text = (last.get("files") or {}).get("app.py")
    diff = res["diff"].replace("--- a/app.py", f"--- a/{src.name}", 1).replace("+++ b/app.py", f"+++ b/{src.name}", 1)
    rec.update({"status": "repaired", "attempts": res["attempts"], "diagnosis": res.get("diagnosis"),
                "differential": res.get("differential"), "diff": diff, "applied": False})
    if o.apply:
        only_app = set(last.get("files") or {}) == {"app.py"}
        try:
            if not only_app or new_text is None:
                raise RuntimeError("the accepted patch touches more than one file; apply the diff by hand")
            repair.apply_patch(src, original, new_text)
            rec["applied"] = True
        except RuntimeError as e:
            rec["apply_error"] = str(e)
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check a list of functions after a library upgrade and repair the silent breaks.")
    ap.add_argument("manifest", help="scan.json with the targets")
    ap.add_argument("--triage-only", action="store_true", help="only classify the targets, no model call")
    ap.add_argument("--fail-on-silent", action="store_true", help="exit 1 if any target is still silent after this run (CI gate; pair with --triage-only)")
    ap.add_argument("--model")
    ap.add_argument("--effort", default="low")
    ap.add_argument("--endpoint", help="base URL of a local OpenAI-compatible server (loopback only, no API key)")
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--only", help="repair only these targets (comma-separated positions in the manifest, from 0); all are still checked")
    ap.add_argument("--token-budget", type=int, default=60000)
    ap.add_argument("--out-dir", default="scan_out", help="where the report and the diffs are written")
    ap.add_argument("--runs-dir", default=str(ROOT / "runs"))
    ap.add_argument("--apply", action="store_true", help="overwrite each repaired file with its accepted patch")
    ap.add_argument("--events", action="store_true", help="print one JSON object per line (progress events) instead of text")
    o = ap.parse_args(argv)
    only = None
    if o.only is not None:
        try:
            only = {int(x) for x in o.only.split(",")}
        except ValueError:
            print("scan: --only wants positions like 0,3,5", file=sys.stderr)
            return 2

    mp = Path(o.manifest)
    if not mp.is_file():
        print(f"scan: {mp} not found", file=sys.stderr)
        return 2
    try:
        targets = json.loads(mp.read_text())["targets"]
        assert isinstance(targets, list) and targets
        for t in targets:
            assert {"file", "function", "lib", "inputs"} <= set(t)
    except (ValueError, KeyError, AssertionError):
        print("scan: the manifest needs a non-empty list 'targets' with file, function, lib and inputs for each", file=sys.stderr)
        return 2
    base = mp.resolve().parent
    out = Path(o.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    def emit(obj: dict) -> None:
        if o.events:
            print(json.dumps(obj), flush=True)

    def say(text: str) -> None:
        if not o.events:
            print(text, flush=True)

    rows = []
    t_start = time.time()
    emit({"event": "start", "total": len(targets), "model": o.model or ("muse-glimmer" if o.endpoint else "muse-spark-1.3"),
          "endpoint": o.endpoint, "triage_only": o.triage_only})
    jobs = []  # (index, src, probes, old, new)
    for k, t in enumerate(targets):  # pass 1: classify every function on both libraries (no model)
        src, probes = base / t["file"], base / t["inputs"]
        old, new = repair.default_python(t["lib"], 0), repair.default_python(t["lib"], 1)
        row = {"file": t["file"], "function": t["function"], "lib": t["lib"], "path": str(src.resolve())}
        if not src.is_file() or not probes.is_file():
            row.update({"status": "invalid", "detail": "file or inputs not found", "example": None})
        elif not old or not new or not Path(old).exists() or not Path(new).exists():
            print(f"scan: no interpreters for {t['lib']} (build them with scripts/setup_envs.sh)", file=sys.stderr)
            return 2
        else:
            status, detail, example = triage(src, t["function"], probes, old, new)
            row.update({"status": status, "detail": detail, "example": example})
            if status == "silent":
                row["source_sha256"] = hashlib.sha256(src.read_bytes()).hexdigest()
                jobs.append((k, src, probes, old, new))
            say(f"[{k + 1}/{len(targets)}] {t['file']}:{t['function']}  {status}: {detail}")
        rows.append(row)
        emit({"event": "triage", "index": k, "row": row})
    if not o.triage_only:
        for k, src, probes, old, new in jobs:  # pass 2: repair the silent ones
            if only is not None and k not in only:
                continue
            t = targets[k]
            emit({"event": "repairing", "index": k})

            def on_attempt(n, rec, k=k):
                emit({"event": "attempt", "index": k, "attempt": view.attempt_view(rec)})
            r = repair_one(src, t["function"], t["lib"], probes, old, new, o, on_attempt)
            diff = r.pop("diff", None)
            rows[k].update(r)
            rows[k]["status"] = r["status"]
            if diff:
                dp = out / f"{Path(t['file']).stem}.{t['function']}.diff"
                dp.write_text(diff)
                rows[k]["diff_file"] = dp.name
            tail = (f"{r.get('attempts')} attempt(s), {r.get('tokens')} tokens, {r.get('seconds')} s"
                    if r["status"] == "repaired" else r.get("detail"))
            say(f"        -> {t['function']}: {r['status']}: {tail}")
            emit({"event": "result", "index": k, "row": {**rows[k], "diff": diff}})

    count = {s: sum(r["status"] == s for r in rows) for s in sorted({r["status"] for r in rows})}
    report = {"manifest": str(mp), "model": o.model or ("muse-glimmer" if o.endpoint else "muse-spark-1.3"),
              "endpoint": o.endpoint, "effort": o.effort, "triage_only": o.triage_only, "applied": o.apply,
              "seconds": round(time.time() - t_start, 1),
              "tokens": sum(r.get("tokens") or 0 for r in rows), "counts": count,
              "targets": [{k: v for k, v in r.items() if k != "path"} for r in rows]}  # no absolute paths in the report
    (out / "scan_report.json").write_text(json.dumps(report, indent=2) + "\n")
    say("\n" + "  ".join(f"{s}: {n}" for s, n in count.items()))
    say(f"report: {out / 'scan_report.json'}")
    emit({"event": "done", "counts": count, "tokens": report["tokens"], "seconds": report["seconds"],
          "report": str(out / "scan_report.json")})
    bad = [r for r in rows if r["status"] in ("not_repaired", "error", "case_failed")]
    if o.fail_on_silent and any(r["status"] == "silent" for r in rows):
        say("fail-on-silent: at least one silent break is left")
        return 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
