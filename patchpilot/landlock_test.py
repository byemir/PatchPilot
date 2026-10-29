"""Linux isolation check with fake secrets (no model call). Skipped on other platforms.

    python -m patchpilot.landlock_test

Runs one probe program twice through sandbox.run: once with isolation off (control: every action must succeed, so the
test cannot pass by accident) and once with isolation on (the actions that model code must not be able to do must fail).
"""
from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
from pathlib import Path

from patchpilot import sandbox

if sys.platform != "linux":
    print("landlock_test: skipped (Linux only; macOS is covered by isolation_test and negative_test)")
    sys.exit(0)

PROBE = r'''
import json, os, socket, sys
secret, repo_file, port, parent = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
home = os.path.dirname(secret)

def t(fn):
    try:
        fn()
        return "allowed"
    except OSError:
        return "denied"

def udp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(b"x", ("127.0.0.1", 9))

def tmpw():
    open("/tmp/pp_landlock_test_" + str(os.getpid()), "w").close()
    os.unlink("/tmp/pp_landlock_test_" + str(os.getpid()))

def homew():
    q = os.path.join(home, ".pp_probe_w_" + str(os.getpid()))
    open(q, "x").close()
    os.unlink(q)

def symlink_escape():
    os.symlink(secret, "link_to_secret")
    open("link_to_secret").read(1)

def imp():
    import numpy
    import pandas
    return numpy, pandas

out = {
    "read_fake_secret": t(lambda: open(secret).read(1)),
    "read_repo_file": t(lambda: open(repo_file).read(1)),
    "list_home": t(lambda: os.listdir(home)),
    "write_home": t(homew),
    "write_tmp": t(tmpw),
    "tcp_to_harness": t(lambda: socket.create_connection(("127.0.0.1", port), timeout=2)),
    "udp_send": t(udp),
    "read_parent_environ": t(lambda: open(f"/proc/{parent}/environ").read(1)),
    "signal_parent": t(lambda: os.kill(parent, 0)),
    "symlink_to_secret": t(symlink_escape),
    "write_workspace": t(lambda: open("ws_file.txt", "w").write("ok")),
    "import_pandas": t(imp),
}
print(json.dumps(out))
'''

passed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed
    assert cond, f"{name}: {detail}"
    passed += 1
    print(f"ok  {name}")


def probe(py: str, secret: Path, repo_file: Path, port: int) -> dict:
    ws = Path(tempfile.mkdtemp(prefix="pp_ll_ws_"))
    try:
        r = sandbox.run(py, ["-c", PROBE, str(secret), str(repo_file), str(port), str(os.getpid())], ws, timeout_s=120)
    finally:
        for f in ws.glob("*"):
            f.unlink(missing_ok=True)
        ws.rmdir()
    assert r.returncode == 0, r.stderr[-400:]
    return json.loads(r.stdout.strip().splitlines()[-1])


repo = Path(__file__).resolve().parents[1]
py = str(repo / ".sandboxes" / "pd23" / "bin" / "python")
repo_file = (sorted((repo / "benchmarks").glob("*/hidden_golden.json")) or [repo / "README.md"])[0]
secret = Path.home() / f".pp_fake_secret_{os.getpid()}"
secret.write_text("fake-secret-not-a-real-key")
srv = socket.socket()
srv.bind(("127.0.0.1", 0))
srv.listen(5)
port = srv.getsockname()[1]
try:
    sandbox.set_fs_deny(False)
    ctrl = probe(py, secret, repo_file, port)
    check("control run without isolation: every action succeeds", set(ctrl.values()) == {"allowed"}, str(ctrl))
    sandbox.set_fs_deny(True)
    sandbox._SELFTESTED.discard(os.path.abspath(py))
    res = probe(py, secret, repo_file, port)
    info = dict(sandbox.LINUX_INFO)
    print("    kernel Landlock ABI", info.get("abi"), "| network namespace", info.get("netns"))
    for k in ("read_fake_secret", "read_repo_file", "list_home", "write_home", "write_tmp", "tcp_to_harness",
              "read_parent_environ", "symlink_to_secret"):
        check(f"isolated: {k} is denied", res[k] == "denied", str(res))
    check("isolated: the workspace is writable", res["write_workspace"] == "allowed", str(res))
    check("isolated: pandas and numpy still import", res["import_pandas"] == "allowed", str(res))
    if info.get("abi", 0) >= 6:
        check("isolated: signalling the harness is denied (ABI 6 or later)", res["signal_parent"] == "denied", str(res))
    else:
        print(f"    signal_parent={res['signal_parent']} (needs Landlock ABI 6; this kernel has {info.get('abi')})")
    if info.get("netns"):
        check("isolated: UDP is denied inside the empty network namespace", res["udp_send"] == "denied", str(res))
    else:
        print(f"    udp_send={res['udp_send']} (no network namespace here; Landlock covers TCP only)")
    sandbox._SELFTESTED.discard(os.path.abspath(py))
    old = sandbox.LINUX_NETNS
    sandbox.LINUX_NETNS = False
    try:
        res2 = probe(py, secret, repo_file, port)
    finally:
        sandbox.LINUX_NETNS = old
    check("Landlock alone (no network namespace): files and TCP still denied",
          all(res2[k] == "denied" for k in ("read_fake_secret", "read_repo_file", "tcp_to_harness")), str(res2))
    print(f"    UDP without a network namespace: {res2['udp_send']}")
    sandbox._SELFTESTED.discard(os.path.abspath(py))
finally:
    secret.unlink(missing_ok=True)
    srv.close()
print(f"landlock_test: {passed} checks passed")
