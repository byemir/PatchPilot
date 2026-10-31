"""Offline check of project mode ("root" in the manifest) on examples/project: a function that imports its sibling module.
Run: python -m patchpilot.project_test   (needs the pinned environments; scripted replies, no model, no network)"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
from pathlib import Path

from patchpilot import agent, meta_client, scan

SRC = Path("examples/project")
FIXES = [('df["low"][df["qty"].map(is_low)] = True', 'df.loc[df["qty"].map(is_low), "low"] = True'),
         ('series.index.astype("int64")', 'series.index.astype("datetime64[ns]").astype("int64")'),
         ("np.array(series.index, dtype=np.int64)", 'np.array(series.index.astype("datetime64[ns]"), dtype=np.int64)')]  # manifest order: flag_low, span_seconds, elapsed_and_values
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


def fake(bad: bool, seen: list, target: Path):
    def chat(messages, model, **kw):
        text = messages[-1]["content"]
        seen.append(text)
        src = target.read_text()
        if not bad:
            fix = FIXES[len(seen) - 1]  # one call per target, in manifest order
            assert fix[0] in src
            src = src.replace(*fix)
        body = json.dumps({"diagnosis": "scripted reply", "files": {"app.py": src}})
        return {"choices": [{"message": {"content": body}}], "usage": {"total_tokens": 100}}
    return chat


orig = meta_client.chat
try:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = tmp / "repo"
        shutil.copytree(SRC, repo)
        before = {p.relative_to(repo).as_posix(): p.read_text() for p in repo.rglob("*.py")}
        rc, out = run([str(repo / "scan.json"), "--triage-only", "--out-dir", str(tmp / "o0")])
        rep = json.loads((tmp / "o0" / "scan_report.json").read_text())
        check("triage with a project root: the function that imports a sibling module runs on both libraries",
              rep["counts"] == {"healthy": 1, "silent": 3}, str(rep["counts"]) + out[-300:])

        seen: list = []
        meta_client.chat = fake(False, seen, repo / "inv" / "stock.py")
        rc, out = run([str(repo / "scan.json"), "--apply", "--max-attempts", "1", "--out-dir", str(tmp / "o1"), "--runs-dir", str(tmp / "runs")])
        rep = json.loads((tmp / "o1" / "scan_report.json").read_text())
        check("the silent break is repaired behind the three gates, exit code 0", rc == 0 and rep["counts"] == {"healthy": 1, "repaired": 3}, out[-500:])
        after = {p.relative_to(repo).as_posix(): p.read_text() for p in repo.rglob("*.py")}
        check("only the target module changed", all(f[1] in after["inv/stock.py"] for f in FIXES)
              and all(after[k] == before[k] for k in before if k != "inv/stock.py"))
        check("the model saw the sibling module as read-only context and could edit only app.py",
              "--- proj/inv/rules.py ---" in seen[0] and seen[0].index("EDITABLE FILES:") < seen[0].index("--- app.py ---") < seen[0].index("READ-ONLY FILES"),
              seen[0][:200])
        check("the diff names the real file", "--- a/stock.py" in (tmp / "o1" / "stock.flag_low.diff").read_text())
        check("a series with a time index is rebuilt from the input and the resolution change is caught and repaired",
              any(t["function"] == "span_seconds" and t["status"] == "repaired" for t in rep["targets"]))
        check("a function that returns a tuple of numpy arrays is compared too (the shape of the real indsl break)",
              any(t["function"] == "elapsed_and_values" and t["status"] == "repaired" for t in rep["targets"]))

        shutil.rmtree(repo)
        shutil.copytree(SRC, repo)
        meta_client.chat = fake(True, [], repo / "inv" / "stock.py")
        rc, out = run([str(repo / "scan.json"), "--apply", "--max-attempts", "1", "--out-dir", str(tmp / "o2"), "--runs-dir", str(tmp / "runs")])
        check("a reply that fixes nothing is rejected and nothing is written",
              rc == 1 and (repo / "inv" / "stock.py").read_text() == before["inv/stock.py"], out[-300:])

        # a module that needs a package the pinned environments do not have is reported as invalid, not repaired
        shutil.rmtree(repo)
        shutil.copytree(SRC, repo)
        (repo / "inv" / "stock.py").write_text("import notapackage_xyz\n" + before["inv/stock.py"])
        rc, out = run([str(repo / "scan.json"), "--triage-only", "--out-dir", str(tmp / "o3")])
        rep = json.loads((tmp / "o3" / "scan_report.json").read_text())
        check("a missing third-party package makes the function invalid, and the error name is shown", rep["counts"] == {"invalid": 4}
              and "ModuleNotFoundError" in rep["targets"][0]["detail"], json.dumps(rep["targets"][0])[:300])

        # a target can name its own interpreters (a project with its own dependencies); the pinned ones are used here
        shutil.rmtree(repo)
        shutil.copytree(SRC, repo)
        envs = Path.cwd() / ".sandboxes"
        m = json.loads((repo / "scan.json").read_text())
        for tg in m["targets"]:
            tg["old"], tg["new"] = str(envs / "pd23" / "bin" / "python"), str(envs / "pd30" / "bin" / "python")
        (repo / "own.json").write_text(json.dumps(m))
        rc, out = run([str(repo / "own.json"), "--triage-only", "--out-dir", str(tmp / "o4")])
        rep = json.loads((tmp / "o4" / "scan_report.json").read_text())
        check("a target with its own old and new interpreter paths is classified the same way", rep["counts"] == {"healthy": 1, "silent": 3}, out[-300:])
        for tg in m["targets"]:
            tg["new"] = str(tmp / "no" / "such" / "python")
        (repo / "own.json").write_text(json.dumps(m))
        rc, out = run([str(repo / "own.json"), "--triage-only", "--out-dir", str(tmp / "o5")])
        check("a missing interpreter path is a setup error with a clear message: exit code 2", rc == 2 and "no usable interpreters" in out, out[-300:])
finally:
    meta_client.chat = orig
print(f"project_test: {passed} checks passed")
