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
FIX = ('df["low"][df["qty"].map(is_low)] = True', 'df.loc[df["qty"].map(is_low), "low"] = True')
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
            assert FIX[0] in src
            src = src.replace(*FIX)
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
              rep["counts"] == {"healthy": 1, "silent": 1}, str(rep["counts"]) + out[-300:])

        seen: list = []
        meta_client.chat = fake(False, seen, repo / "inv" / "stock.py")
        rc, out = run([str(repo / "scan.json"), "--apply", "--max-attempts", "1", "--out-dir", str(tmp / "o1"), "--runs-dir", str(tmp / "runs")])
        rep = json.loads((tmp / "o1" / "scan_report.json").read_text())
        check("the silent break is repaired behind the three gates, exit code 0", rc == 0 and rep["counts"] == {"healthy": 1, "repaired": 1}, out[-500:])
        after = {p.relative_to(repo).as_posix(): p.read_text() for p in repo.rglob("*.py")}
        check("only the target module changed", FIX[1] in after["inv/stock.py"]
              and all(after[k] == before[k] for k in before if k != "inv/stock.py"))
        check("the model saw the sibling module as read-only context and could edit only app.py",
              "--- proj/inv/rules.py ---" in seen[0] and seen[0].index("EDITABLE FILES:") < seen[0].index("--- app.py ---") < seen[0].index("READ-ONLY FILES"),
              seen[0][:200])
        check("the diff names the real file", "--- a/stock.py" in (tmp / "o1" / "stock.flag_low.diff").read_text())

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
        check("a missing third-party package makes the function invalid, and the error name is shown", rep["counts"] == {"invalid": 2}
              and "ModuleNotFoundError" in rep["targets"][0]["detail"], json.dumps(rep["targets"][0])[:300])
finally:
    meta_client.chat = orig
print(f"project_test: {passed} checks passed")
