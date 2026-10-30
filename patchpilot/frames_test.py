"""Offline check of DataFrame inputs and outputs ("$df") on examples/frames: triage, repair with scripted replies, capture.
Run: python -m patchpilot.frames_test   (needs the pinned environments from scripts/setup_envs.sh; no model, no network)"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
from pathlib import Path

from patchpilot import capture, make_case, meta_client, repair, scan

SRC = Path("examples/frames")
FIXES = {
    "fill_missing": [('df["age"].fillna(df["age"].median(), inplace=True)', 'df["age"] = df["age"].fillna(df["age"].median())'),
                     ('df["income"].fillna(0, inplace=True)', 'df["income"] = df["income"].fillna(0)')],
    "flag_outliers": [('df["outlier"][df["income"] > limit] = 1', 'df.loc[df["income"] > limit, "outlier"] = 1')],
    "add_signup_seconds": [('pd.to_datetime(df["signup"]).astype("int64")',
                            'pd.to_datetime(df["signup"]).astype("datetime64[ns]").astype("int64")')],
}
passed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed
    assert cond, f"{name}: {detail}"
    passed += 1
    print(f"ok  {name}")


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = scan.main(argv)
    return rc, buf.getvalue()


def fake(bad: bool, target: Path):
    calls = []

    def chat(messages, model, **kw):  # one call per target, in manifest order (the module holds all functions, so the prompt cannot tell which)
        fn = list(FIXES)[len(calls)]
        calls.append(fn)
        src = target.read_text()  # the file as the scan sees it now
        if not bad:
            for old, new in FIXES[fn]:
                assert old in src
                src = src.replace(old, new)
        body = json.dumps({"diagnosis": "scripted reply", "files": {"app.py": src}})
        return {"choices": [{"message": {"content": body}}], "usage": {"total_tokens": 100}}
    return chat


check("the plain runner is used when no input has a table, the table runner when one does",
      make_case.templates("f", [{"x": 1}])[0] is make_case.RUN and make_case.templates("f", [{"df": {"$df": {"a": [1]}}}])[0] is make_case.RUN_DF)
orig = meta_client.chat
try:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = tmp / "repo"
        shutil.copytree(SRC, repo)
        rc, out = run([str(repo / "scan.json"), "--triage-only", "--out-dir", str(tmp / "o0")])
        rep = json.loads((tmp / "o0" / "scan_report.json").read_text())
        names = {r["function"]: r["status"] for r in rep["targets"]}
        check("triage on DataFrame inputs: three silent breaks, three healthy",
              rep["counts"] == {"healthy": 3, "silent": 3} and names["fill_missing"] == "silent" and names["clean_names"] == "healthy", str(rep["counts"]))
        ex = next(r["example"] for r in rep["targets"] if r["function"] == "add_signup_seconds")
        check("the example shows the table that was passed and both results",
              "$df" in json.dumps(ex["input"]) and ex["old"]["$df"]["signup_s"] != ex["new"]["$df"]["signup_s"], json.dumps(ex)[:300])

        meta_client.chat = fake(False, repo / "frames" / "prep.py")
        rc, out = run([str(repo / "scan.json"), "--apply", "--max-attempts", "1", "--out-dir", str(tmp / "o1"), "--runs-dir", str(tmp / "runs")])
        rep = json.loads((tmp / "o1" / "scan_report.json").read_text())
        check("the three silent breaks are repaired behind the gates, exit code 0",
              rc == 0 and rep["counts"] == {"healthy": 3, "repaired": 3}, out[-600:] + str(rep["counts"]))
        after = (repo / "frames" / "prep.py").read_text()
        check("the accepted patches were applied and nothing else changed",
              all(new in after and old not in after for fx in FIXES.values() for old, new in fx)
              and after.count("def ") == (SRC / "frames" / "prep.py").read_text().count("def "))
        rc, out = run([str(repo / "scan.json"), "--triage-only", "--out-dir", str(tmp / "o2")])
        check("after the repair every function is healthy", json.loads((tmp / "o2" / "scan_report.json").read_text())["counts"] == {"healthy": 6}, out[-300:])

        shutil.rmtree(repo)
        shutil.copytree(SRC, repo)
        meta_client.chat = fake(True, repo / "frames" / "prep.py")
        rc, out = run([str(repo / "scan.json"), "--apply", "--max-attempts", "1", "--out-dir", str(tmp / "o3"), "--runs-dir", str(tmp / "runs")])
        rep = json.loads((tmp / "o3" / "scan_report.json").read_text())
        check("a reply that fixes nothing is rejected and the file is untouched",
              rc == 1 and rep["counts"] == {"healthy": 3, "not_repaired": 3}
              and (repo / "frames" / "prep.py").read_text() == (SRC / "frames" / "prep.py").read_text(), str(rep["counts"]))

        # capture: a DataFrame argument is recorded as a table; a frame with a custom index is skipped, not mangled
        old = repair.default_python("pandas", 0)
        proj = tmp / "proj"
        shutil.copytree(SRC, proj)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = capture.main(["--python", old, "--discover", str(proj / "frames" / "prep.py"), "--out", str(proj / "p2"),
                               "--manifest", str(proj / "m2.json"), "--lib", "pandas", "--cwd", str(proj), "--", "-m", "unittest", "discover", "tests"])
        probes = json.loads((proj / "p2" / "fill_missing.json").read_text())
        check("capture records a DataFrame argument as a table, missing values as null",
              rc == 0 and probes[0]["df"]["$df"]["age"][1] is None and len(probes[0]["df"]["$df"]["name"]) == 4, buf.getvalue()[-400:])
finally:
    meta_client.chat = orig
print(f"frames_test: {passed} checks passed")
