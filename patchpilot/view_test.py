"""Offline check of the viewer (no browser, no model, no network beyond 127.0.0.1).

    python -m patchpilot.view_test
"""
from __future__ import annotations

import json
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from patchpilot import view

passed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed
    assert cond, f"{name}: {detail}"
    passed += 1
    print(f"ok  {name}")


ok = {"old_verdict": "OK", "new_verdict": "OK", "hidden_old": "OK", "hidden_new": "OK", "differential": {"verdict": "PASS"}, "success": True}
check("accepted attempt: all three gates passed", view.gates_of(ok) == {"visible": "ok", "hidden": "ok", "differential": "ok", "outcome": "accepted"})
check("visible failure skips the later gates", view.gates_of({"old_verdict": "OK", "new_verdict": "SILENT_BREAKAGE"})
      == {"visible": "fail", "hidden": "skipped", "differential": "skipped", "outcome": "rejected at the visible tests"})
check("hidden failure after passing the visible tests", view.gates_of({**ok, "hidden_new": "SILENT_BREAKAGE", "differential": None, "success": False})["outcome"]
      == "rejected at the hidden tests")
check("differential rejection", view.gates_of({**ok, "differential": {"verdict": "DIVERGENCE"}, "success": False})["outcome"]
      == "rejected at the differential check")
check("invalid reply", view.gates_of({"error": "no JSON"})["outcome"] == "invalid reply")
check("differential off is shown as off", view.gates_of({**ok, "differential": None})["differential"] == "off")
ex = {"tier": "core", "probe": {"f": ["0", "00"]}, "expected": [False, False], "got": [False, True], "where": "new"}
av = view.attempt_view({**ok, "attempt": 1, "differential": {"verdict": "DIVERGENCE", "examples": [ex], "core_divergences": 3}, "success": False})
check("the counterexample is passed on", av["counterexample"]["got"] == [False, True] and av["differential"]["core_divergences"] == 3)

with tempfile.TemporaryDirectory() as t:
    tmp = Path(t)
    run = tmp / "runs" / "r1"
    run.mkdir(parents=True)
    (run / "attempt_1.json").write_text(json.dumps({**ok, "attempt": 1, "old_verdict": "OK", "new_verdict": "SILENT_BREAKAGE", "success": False}))
    (run / "attempt_2.json").write_text(json.dumps({**ok, "attempt": 2}))
    (run / "patch.diff").write_text("--- a/x.py\n+++ b/x.py\n@@\n-a\n+b\n")
    rep = {"model": "m", "counts": {"repaired": 1}, "targets": [
        {"file": "x.py", "function": "f", "lib": "pandas", "status": "repaired", "detail": "d", "attempts": 2, "run_dir": str(run)},
        {"file": "y.py", "function": "g", "lib": "pandas", "status": "healthy", "detail": "same"},
        {"file": "z.py", "function": "h", "lib": "pandas", "status": "repaired", "run_dir": str(tmp / "elsewhere")}]}
    (tmp / "scan_report.json").write_text(json.dumps(rep))

    class A:
        report, run, runs_root = str(tmp / "scan_report.json"), None, str(tmp / "runs")
    data = view.build(A)
    t0 = data["targets"][0]
    check("a report is joined with its run records", [a["gates"]["outcome"] for a in t0["attempts"]] == ["rejected at the visible tests", "accepted"]
          and "+b" in t0["diff"])
    check("a run folder outside --runs-root is not read", "diff" not in data["targets"][2] and not isinstance(data["targets"][2].get("attempts"), list))

    srv = ThreadingHTTPServer(("127.0.0.1", 0), view.make_handler(data))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    page = urllib.request.urlopen(base + "/").read().decode()
    got = json.loads(urllib.request.urlopen(base + "/api/data").read())
    check("the server returns the page and the data", "<title>PatchPilot scan</title>" in page and got["targets"][0]["function"] == "f")
    try:
        urllib.request.urlopen(base + "/etc/passwd")
        check("other paths are not served", False)
    except urllib.error.HTTPError as e:
        check("other paths are not served", e.code == 404)
    srv.shutdown()
    check("the server listens on the loopback address only", srv.server_address[0] == "127.0.0.1")
print(f"view_test: {passed} checks passed")
