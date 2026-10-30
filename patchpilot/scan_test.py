"""Offline check of the scan command with scripted model replies (no model, no key, no network).

    python -m patchpilot.scan_test
"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
from pathlib import Path

from patchpilot import meta_client, scan

SRC = Path("examples/sample_repo")
FIXES = {  # function -> (old text, new text) of the known-good fix
    "span_seconds": ('ticks = parsed.astype("int64")', 'ticks = parsed.astype("datetime64[ns]").astype("int64")'),
    "late_flags": ('table["late"].iloc[position] = 1', 'table.loc[position, "late"] = 1'),
    "counts_by_size": ('table.groupby("size").size()', 'table.groupby("size", observed=False).size()'),
    "hot_readings_text": ("str(list(arr[arr > threshold]))", "str([float(x) for x in arr[arr > threshold]])"),
    "total_with_tax": ("float(np.float32(p) * (1.0 + rate))", "float(np.float64(np.float32(p)) * (1.0 + rate))"),
}
passed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed
    assert cond, f"{name}: {detail}"
    passed += 1
    print(f"ok  {name}")


def find(path: Path, fn: str) -> Path:
    return next(p for p in path.rglob("*.py") if f"def {fn}(" in p.read_text())


def script(bad: bool = False):
    def fake(messages, model, **kw):
        text = messages[-1]["content"]
        fn = next(f for f in FIXES if f"def {f}(" in text)
        src = find(SRC, fn).read_text()
        if not bad:
            old, new = FIXES[fn]
            assert old in src
            src = src.replace(old, new)
        body = json.dumps({"diagnosis": "scripted reply", "files": {"app.py": src}})
        return {"choices": [{"message": {"content": body}}], "usage": {"total_tokens": 100}}
    meta_client.chat = fake


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = scan.main(argv)
    return rc, buf.getvalue()


orig = meta_client.chat
try:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = tmp / "repo"
        shutil.copytree(SRC, repo)
        before = {p.name: p.read_text() for p in repo.rglob("*.py")}

        def boom(*a, **k):
            raise AssertionError("the model must not be called with --triage-only")
        meta_client.chat = boom
        rc, out = run([str(repo / "scan.json"), "--triage-only", "--out-dir", str(tmp / "o0")])
        rep = json.loads((tmp / "o0" / "scan_report.json").read_text())
        check("triage classifies the sample repo", rep["counts"] == {"healthy": 2, "loud": 1, "silent": 5} and rc == 0, str(rep["counts"]))
        check("triage-only calls no model and changes no file", {p.name: p.read_text() for p in repo.rglob("*.py")} == before)

        script()
        rc, out = run([str(repo / "scan.json"), "--apply", "--max-attempts", "1", "--out-dir", str(tmp / "o1"),
                       "--runs-dir", str(tmp / "runs")])
        rep = json.loads((tmp / "o1" / "scan_report.json").read_text())
        check("all five silent breaks are repaired, exit code 0",
              rc == 0 and rep["counts"] == {"healthy": 2, "loud": 1, "repaired": 5}, out[-600:] + str(rep["counts"]))
        after = {p.name: p.read_text() for p in repo.rglob("*.py")}
        for fn, (a, b) in FIXES.items():
            f = find(repo, fn).name
            check(f"{fn}: the accepted patch was applied", b in after[f] and a not in after[f])
        check("healthy and loud files are untouched", after["weekly_totals.py"] == before["weekly_totals.py"]
              and after["normalize.py"] == before["normalize.py"] and after["total_volume.py"] == before["total_volume.py"])
        check("a diff is written per repaired function", len(list((tmp / "o1").glob("*.diff"))) == 5)
        check("the report carries the gate outcome of every attempt", all(
            r["attempts_detail"][-1]["gates"]["outcome"] == "accepted" for r in rep["targets"] if r["status"] == "repaired"))

        shutil.rmtree(repo)
        shutil.copytree(SRC, repo)
        one = {"targets": [t for t in json.loads((repo / "scan.json").read_text())["targets"] if t["function"] == "span_seconds"]}
        (repo / "one.json").write_text(json.dumps(one))
        script(bad=True)
        rc, out = run([str(repo / "one.json"), "--apply", "--max-attempts", "1", "--out-dir", str(tmp / "o2"),
                       "--runs-dir", str(tmp / "runs")])
        rep = json.loads((tmp / "o2" / "scan_report.json").read_text())
        check("a patch that fixes nothing is not accepted: exit code 1, file untouched",
              rc == 1 and rep["targets"][0]["status"] == "not_repaired"
              and (repo / "analytics" / "session_span.py").read_text() == before["session_span.py"], out[-400:])
        script()
        rc, out = run([str(repo / "scan.json"), "--only", "0", "--max-attempts", "1", "--out-dir", str(tmp / "o3"), "--runs-dir", str(tmp / "runs")])
        rep = json.loads((tmp / "o3" / "scan_report.json").read_text())
        check("--only repairs just the chosen target; the others are still checked",
              rep["counts"] == {"healthy": 2, "loud": 1, "repaired": 1, "silent": 4} and rep["targets"][0]["status"] == "repaired", str(rep["counts"]))
        check("--only with a bad value: exit code 2", run([str(repo / "scan.json"), "--only", "a"])[0] == 2)
        (repo / "bad.json").write_text("{}")
        rc, out = run([str(repo / "bad.json")])
        check("a manifest without targets: exit code 2", rc == 2)
finally:
    meta_client.chat = orig
print(f"scan_test: {passed} checks passed")
