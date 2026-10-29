"""Offline check of the repair command with a scripted model reply (no model, no key, no network).

    python -m patchpilot.repair_test
"""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
from pathlib import Path

from patchpilot import meta_client, repair

B = Path("benchmarks/n8_string_to_bool")
NP = (".sandboxes/np126/bin/python", ".sandboxes/np2/bin/python")
GOOD = json.loads((B / "known_good.json").read_text())["files"]["app.py"]
BAD = json.loads((B / "known_bad" / "not_zero_string.json").read_text())["files"]["app.py"]
passed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed
    assert cond, f"{name}: {detail}"
    passed += 1
    print(f"ok  {name}")


def script(reply_app: str):
    body = json.dumps({"diagnosis": "scripted reply", "files": {"app.py": reply_app}})
    def fake(messages, model, **kw):
        return {"choices": [{"message": {"content": body}}], "usage": {"total_tokens": 100}}
    meta_client.chat = fake


def run(tmp: Path, name: str, fn: str, *extra) -> tuple[int, str, Path, Path]:
    work = tmp / name
    work.mkdir()
    f = work / "my_func.py"
    shutil.copy(B / "app.py", f)
    argv = [str(f), fn, "--inputs", str(B / "inputs.json"), "--lib", "numpy", "--old", NP[0], "--new", NP[1],
            "--out-dir", str(work / "out"), "--runs-dir", str(work / "runs"), *extra]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = repair.main(argv)
    return rc, buf.getvalue(), f, work / "out"


orig = meta_client.chat
try:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        source = (B / "app.py").read_text()
        script(GOOD)
        rc, out, f, o = run(tmp, "good", "enabled_devices", "--max-attempts", "1")
        d = o / "my_func.enabled_devices.patchpilot.diff"
        rep = json.loads((o / "my_func.enabled_devices.patchpilot.json").read_text())
        check("accepted patch: exit code 0", rc == 0, out[-400:])
        check("without --apply the file is untouched", f.read_text() == source)
        check("the diff names the user's file", d.exists() and "--- a/my_func.py" in d.read_text())
        check("the report records the run", rep["success"] and rep["applied"] is False and rep["attempts"] == 1, str(rep))
        rc, out, f, o = run(tmp, "apply", "enabled_devices", "--max-attempts", "1", "--apply")
        check("--apply overwrites the file with the accepted patch", rc == 0 and f.read_text() == GOOD, out[-400:])
        script(BAD)
        rc, out, f, o = run(tmp, "bad", "enabled_devices", "--max-attempts", "1", "--apply")
        check("rejected patch: exit code 1, file untouched, no diff", rc == 1 and f.read_text() == source and not o.exists(), out[-400:])
        rc, out, f, o = run(tmp, "nofn", "no_such_function")
        check("unknown function: exit code 2, file untouched", rc == 2 and f.read_text() == source, out[-300:])
        p = tmp / "changed.py"
        p.write_text("x")
        try:
            repair.apply_patch(p, "y", "z")
            check("a file changed after the case was built is not overwritten", False)
        except RuntimeError:
            check("a file changed after the case was built is not overwritten", p.read_text() == "x")
finally:
    meta_client.chat = orig
print(f"repair_test: {passed} checks passed")
