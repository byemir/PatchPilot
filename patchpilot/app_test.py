"""Offline tests for the browser app (no model, no network). Run: python -m patchpilot.app_test"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from patchpilot import app as appmod

REPO = Path(__file__).resolve().parent.parent
FAILS: list[str] = []


def check(name: str, ok: bool) -> None:
    print(("ok   " if ok else "FAIL ") + name)
    if not ok:
        FAILS.append(name)


def call(app, path, body=None, token=True, host=None, origin=None):
    h = {"Host": host or f"127.0.0.1:{app.port}"}
    if token:
        h["X-PatchPilot-Token"] = app.token
    if origin:
        h["Origin"] = origin
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(f"http://127.0.0.1:{app.port}{path}", data=data, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if r.headers.get("Content-Type", "").startswith("application/json") else raw)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw


def wait(app, want, limit=90):
    t0 = time.time()
    while time.time() - t0 < limit:
        if app.job and app.job.status in want:
            return True
        time.sleep(0.05)
    return False


def project(root: Path) -> Path:
    p = root / "proj"
    p.mkdir()
    (p / "mod.py").write_text("def f(x):\n    return x\n")
    (p / "in.json").write_text("[{\"x\": 1}]")
    (p / "scan.json").write_text(json.dumps({"targets": [{"file": "mod.py", "function": "f", "lib": "numpy", "inputs": "in.json"}]}))
    (p / "other.json").write_text("{\"hello\": 1}")
    return p


def fake_runner(src: Path, files, hold=None):
    """Plays one repaired function: the events a real scan would print."""
    def run(argv, on_line, holder):
        out = Path(argv[argv.index("--out-dir") + 1])
        rd = out / "runs" / "r1"
        rd.mkdir(parents=True)
        (rd / "attempt_1.json").write_text(json.dumps({"files": files}))
        emit = lambda o: on_line(json.dumps(o) + "\n")
        emit({"event": "start", "total": 1})
        row = {"file": "mod.py", "function": "f", "lib": "numpy", "status": "silent", "detail": "d", "example": None,
               "path": str(src), "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
        emit({"event": "triage", "index": 0, "row": row})
        emit({"event": "repairing", "index": 0})
        emit({"event": "result", "index": 0, "row": {**row, "status": "repaired", "attempts": 1, "run_dir": str(rd), "diff": "--- a\n+++ b\n"}})
        if hold:
            hold.wait(30)
        emit({"event": "done", "counts": {"repaired": 1}, "tokens": 1, "seconds": 1, "report": "x"})
        return 0
    return run


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    try:
        root = tmp / "root"
        root.mkdir()
        proj = project(root)
        src = proj / "mod.py"
        app, srv = appmod.serve(root, 0)
        threading.Thread(target=srv.serve_forever, daemon=True).start()

        code, page = call(app, "/", token=False)
        check("the page carries this run's token", code == 200 and app.token.encode() in page)
        check("a wrong Host header is refused (DNS rebinding)", call(app, "/", token=False, host="evil.example:80")[0] == 403)
        check("an API call without the token is refused", call(app, "/api/state", token=False)[0] == 403)
        check("a foreign Origin is refused", call(app, "/api/run", {"manifest": "proj/scan.json", "mode": "check"}, origin="http://evil.example")[0] == 403)
        code, st = call(app, "/api/state")
        check("only real scan manifests are listed", code == 200 and st["manifests"] == ["proj/scan.json"])
        check("the state says whether the pinned environments exist", isinstance(st["envs"], bool))
        check("no hosted model is offered without a key", st["hosted"] == [] or appmod.meta_client.KEY_PATH.exists())

        bad = [{"manifest": "../x.json", "mode": "check"}, {"manifest": "proj/other.json", "mode": "check"}, {"manifest": "proj/scan.json", "mode": "rm"},
               {"manifest": "proj/scan.json", "mode": "repair", "model": "local", "endpoint": "http://example.com:8080/v1"},
               {"manifest": "proj/scan.json", "mode": "repair", "model": "gpt-9"},
               {"manifest": "proj/scan.json", "mode": "check", "max_attempts": 99}]
        check("bad requests are refused (path, mode, remote endpoint, model, attempts)", all(call(app, "/api/run", b)[0] == 400 for b in bad) and app.job is None)
        check("a remote health probe is refused", call(app, "/api/health?endpoint=http%3A%2F%2Fexample.com%3A80%2Fv1")[1]["ok"] is False)

        # events flow, paths stay on the server, second run refused, stop works
        hold = threading.Event()
        app.runner = fake_runner(src, {"app.py": "def f(x):\n    return x + 0\n"}, hold)
        code, r = call(app, "/api/run", {"manifest": "proj/scan.json", "mode": "repair", "model": "local", "endpoint": "http://127.0.0.1:8080/v1"})
        check("a run starts", code == 200 and wait(app, ("running",)))
        time.sleep(0.4)
        check("a second run is refused while one is running", call(app, "/api/run", {"manifest": "proj/scan.json", "mode": "check"})[0] == 409)
        _, j = call(app, "/api/job?since=0")
        wire = json.dumps(j)
        check("events arrive and carry no absolute path or hash", [e["event"] for e in j["events"]] == ["start", "triage", "repairing", "result"]
              and str(tmp) not in wire and "source_sha256" not in wire)
        _, j2 = call(app, f"/api/job?since={j['n']}")
        check("the cursor returns only new events", j2["events"] == [])
        check("stop is accepted", call(app, "/api/stop", {})[0] == 200)
        hold.set()
        check("a stopped job ends as stopped", wait(app, ("stopped", "done")) and app.job.status == "stopped")

        # NaN in a function's output must still reach the browser as valid JSON
        def nan_runner(argv, on_line, holder):
            on_line(json.dumps({"event": "start", "total": 1}) + "\n")
            on_line(json.dumps({"event": "attempt", "index": 0, "attempt": {"attempt": 1, "gates": {"outcome": "x"}, "counterexample": {"expected": float("nan"), "got": float("inf")}}}) + "\n")
            on_line(json.dumps({"event": "done", "counts": {}, "tokens": 0, "seconds": 0, "report": "x"}) + "\n")
            return 0
        app.runner = nan_runner
        call(app, "/api/run", {"manifest": "proj/scan.json", "mode": "check"})
        wait(app, ("done",))
        _, j = call(app, "/api/job?since=0")
        check("NaN and Infinity reach the page as text, not as invalid JSON", j["events"][1]["attempt"]["counterexample"] == {"expected": "nan", "got": "inf"})

        # apply
        app.runner = fake_runner(src, {"app.py": "def f(x):\n    return x + 0\n"})
        call(app, "/api/run", {"manifest": "proj/scan.json", "mode": "check"})
        check("the job finishes", wait(app, ("done",)) and app.job.status == "done")
        check("apply of an unknown index is refused", call(app, "/api/apply", {"index": 7})[0] == 400)
        before = src.read_text()
        src.write_text(before + "# edited\n")
        code, r = call(app, "/api/apply", {"index": 0})
        check("apply is refused when the file changed since the scan", code == 409 and src.read_text() == before + "# edited\n")
        src.write_text(before)
        code, r = call(app, "/api/apply", {"index": 0})
        check("apply writes the accepted patch", code == 200 and src.read_text() == "def f(x):\n    return x + 0\n")
        check("a second apply is refused", call(app, "/api/apply", {"index": 0})[0] == 409)

        # undo
        check("undo before any apply is refused", call(app, "/api/undo", {"index": 3})[0] in (400, 409))
        code, r = call(app, "/api/undo", {"index": 0})
        check("undo puts the original file back", code == 200 and src.read_text() == before)
        check("a second undo is refused", call(app, "/api/undo", {"index": 0})[0] == 409)
        check("apply works again after undo", call(app, "/api/apply", {"index": 0})[0] == 200)
        src.write_text(src.read_text() + "# mine\n")
        code, r = call(app, "/api/undo", {"index": 0})
        check("undo is refused when the file was edited after Apply", code == 409 and src.read_text().endswith("# mine\n"))
        src.write_text(before)
        check("an unknown job id is refused", call(app, "/api/apply", {"index": 0, "job": "nope"})[0] == 400)

        # reset: the folder goes back to what it was before the app wrote anything
        src.write_text(before)
        app.runner = fake_runner(src, {"app.py": "def f(x):\n    return x + 2\n"})
        call(app, "/api/run", {"manifest": "proj/scan.json", "mode": "check"})
        wait(app, ("done",))
        check("nothing is changed before the first write", call(app, "/api/state")[1]["changed"] == 0)
        call(app, "/api/apply", {"index": 0})
        check("the state counts the files the app wrote", call(app, "/api/state")[1]["changed"] == 1 and src.read_text().endswith("x + 2\n"))
        code, r = call(app, "/api/reset", {})
        check("reset puts the file back and marks the row as not applied", code == 200 and r["restored"] == 1 and r["skipped"] == [] and src.read_text() == before
              and app.job.rows[0]["applied"] is False and call(app, "/api/state")[1]["changed"] == 0)
        code, r = call(app, "/api/reset", {})
        check("a second reset has nothing to do", code == 200 and r["restored"] == 0)
        check("the patch can be applied again after a reset", call(app, "/api/apply", {"index": 0})[0] == 200 and src.read_text().endswith("x + 2\n"))
        src.write_text(src.read_text() + "# mine\n")
        code, r = call(app, "/api/reset", {})
        check("reset leaves a file alone that was edited by hand", code == 200 and r["restored"] == 0 and r["skipped"] == ["proj/mod.py"] and src.read_text().endswith("# mine\n"))
        src.write_text(before)
        call(app, "/api/reset", {})
        hold2 = threading.Event()
        app.runner = fake_runner(src, {"app.py": "x = 1\n"}, hold2)
        call(app, "/api/run", {"manifest": "proj/scan.json", "mode": "check"})
        wait(app, ("running",))
        time.sleep(0.4)
        check("reset is refused while a run is in progress", call(app, "/api/reset", {})[0] == 409)
        hold2.set()
        wait(app, ("done",))
        check("reset needs the token", call(app, "/api/reset", {}, token=False)[0] == 403)
        src.write_text(before)

        src.write_text(before)
        app.runner = fake_runner(src, {"app.py": "x = 1\n", "other.py": "y = 2\n"})
        call(app, "/api/run", {"manifest": "proj/scan.json", "mode": "check"})
        wait(app, ("done",))
        code, r = call(app, "/api/apply", {"index": 0})
        check("a patch touching two files is not applied", code == 409 and src.read_text() == before)

        # an older job can still be applied after a newer one started
        app.runner = fake_runner(src, {"app.py": "def f(x):\n    return x + 1\n"})
        call(app, "/api/run", {"manifest": "proj/scan.json", "mode": "check"})
        wait(app, ("done",))
        id_a = app.job.id
        app.runner = fake_runner(src, {"app.py": "x = 2\n"})
        call(app, "/api/run", {"manifest": "proj/scan.json", "mode": "check"})
        wait(app, ("done",))
        check("a new job does not hide the rows of an older one", app.job.id != id_a
              and call(app, "/api/apply", {"index": 0, "job": id_a})[0] == 200 and src.read_text() == "def f(x):\n    return x + 1\n")
        call(app, "/api/undo", {"index": 0, "job": id_a})
        src.write_text(before)

        # one row only, and the hosted model choice
        seen = []
        inner = fake_runner(src, {"app.py": "x = 1\n"})
        app.runner = lambda argv, on_line, holder: (seen.append(argv), inner(argv, on_line, holder))[1]
        base = {"manifest": "proj/scan.json", "mode": "repair", "model": "local", "endpoint": "http://127.0.0.1:8080/v1"}
        check("a bad row selection is refused", all(call(app, "/api/run", {**base, "only": o})[0] == 400 for o in ([], [1], [-1], [True], "0")))
        code, r = call(app, "/api/run", {**base, "only": [0]})
        wait(app, ("done",))
        a = seen[-1]
        check("one row is repaired with --only", code == 200 and a[a.index("--only") + 1] == "0" and "--endpoint" in a)
        key = tmp / "key"
        key.write_text("SECRET-KEY-VALUE")
        saved = appmod.meta_client.KEY_PATH
        appmod.meta_client.KEY_PATH = key
        try:
            check("a hosted model is offered only when the key file exists", call(app, "/api/state")[1]["hosted"] == list(appmod.HOSTED))
            code, r = call(app, "/api/run", {"manifest": "proj/scan.json", "mode": "repair", "model": "muse-spark-1.3"})
            wait(app, ("done",))
            a = seen[-1]
            check("a hosted model run passes --model and no local endpoint", code == 200 and a[a.index("--model") + 1] == "muse-spark-1.3" and "--endpoint" not in a)
            check("the page and the job events never contain the key", "SECRET-KEY-VALUE" not in json.dumps(call(app, "/api/state")[1]) + json.dumps(call(app, "/api/job?since=0")[1]))
        finally:
            appmod.meta_client.KEY_PATH = saved

        # real subprocess, check only, on the sample repository
        shutil.copytree(REPO / "examples" / "sample_repo", root / "sample")
        app.runner = appmod.subprocess_runner
        code, r = call(app, "/api/run", {"manifest": "sample/scan.json", "mode": "check"})
        ok = code == 200 and wait(app, ("done", "failed"), 120)
        _, j = call(app, "/api/job?since=0")
        tri = [e for e in j["events"] if e["event"] == "triage"]
        done = [e for e in j["events"] if e["event"] == "done"]
        check("a real check job runs the scan in a subprocess", ok and j["status"] == "done" and len(tri) == 8 and done
              and done[0]["counts"] == {"healthy": 2, "loud": 1, "silent": 5})
        check("a check job writes no model call and changes no file", (root / "sample" / "analytics" / "session_span.py").read_text()
              == (REPO / "examples" / "sample_repo" / "analytics" / "session_span.py").read_text())
        _, st = call(app, "/api/state")
        rid = st["previous"][0]["id"]
        code, rep = call(app, "/api/report?id=" + rid)
        check("a past run can be read back", code == 200 and len(rep["targets"]) == 8)
        check("a bad run id is refused", call(app, "/api/report?id=..%2F..")[0] == 400)
        srv.shutdown()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"app_test: {'all checks passed' if not FAILS else str(len(FAILS)) + ' FAILED'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
