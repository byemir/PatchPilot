"""Isolation self-test with FAKE secrets only; the real key is never used, read or printed.

Two harness variants, each started in its own clean child process:
  env: a fake secret (CANARY_ENV_TOKEN) is in the harness's INITIAL environment
  mem: the initial environment is clean; a fake secret exists only as a string in the harness's memory
A script playing the role of model code then tries to reach the fake secrets and other protected things:
first without the OS profile (control: a leak must be visible there, otherwise the probe proves nothing),
then with the production profile, then with a default-deny candidate profile.

  python -m patchpilot.isolation_test
  python -m patchpilot.isolation_test --reexec-check    # names of the initial environment after the clean re-exec
"""
from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

from patchpilot import sandbox

REPO = Path(__file__).resolve().parents[1]
OPEN_VALUES = {"VISIBLE", "OPEN", "PORT OBTAINED"}

PROBE = r'''
import ctypes, ctypes.util, json, os, socket, subprocess, sys
marker_env, marker_mem, canary_file, hidden_abs, port = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
res = {}
ppid = os.getppid()
libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)


def attempt(fn):
    try:
        fn()
        return "OPEN"
    except PermissionError:
        return "BLOCKED"
    except Exception as e:
        return "other:" + type(e).__name__


def procargs(pid):
    mib = (ctypes.c_int * 3)(1, 49, pid)
    size = ctypes.c_size_t(0)
    if libc.sysctl(mib, 3, None, ctypes.byref(size), None, 0) != 0:
        return None, "errno " + str(ctypes.get_errno())
    buf = ctypes.create_string_buffer(size.value)
    if libc.sysctl(mib, 3, buf, ctypes.byref(size), None, 0) != 0:
        return None, "errno " + str(ctypes.get_errno())
    return buf.raw[: size.value], ""


data, err = procargs(ppid)
if data is None:
    res["sysctl procargs: env canary"] = res["sysctl procargs: memory-only canary"] = "no data (" + err + ")"
else:
    res["sysctl procargs: env canary"] = "VISIBLE" if marker_env.encode() in data else "not visible"
    res["sysctl procargs: memory-only canary"] = "VISIBLE" if marker_mem.encode() in data else "not visible"

try:
    r = subprocess.run(["/bin/ps", "-wwE", "-p", str(ppid)], capture_output=True, text=True, timeout=10)
    res["ps -E: env canary"] = "VISIBLE" if marker_env in r.stdout else "not visible"
except PermissionError:
    res["ps -E: env canary"] = "BLOCKED"
except Exception as e:
    res["ps -E: env canary"] = "other:" + type(e).__name__

try:
    lib = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
    me = ctypes.c_uint.in_dll(lib, "mach_task_self_").value
    port_ = ctypes.c_uint(0)
    kr = lib.task_for_pid(ctypes.c_uint(me), ctypes.c_int(ppid), ctypes.byref(port_))
    res["task_for_pid(harness)"] = "PORT OBTAINED" if kr == 0 else "refused (kern_return %d)" % kr
except Exception as e:
    res["task_for_pid(harness)"] = "other:" + type(e).__name__

res["read fake secret file under ~/.config"] = attempt(lambda: open(canary_file).read(1))
res["read repo hidden_golden.json (absolute)"] = attempt(lambda: open(hidden_abs).read(1))
res["read hidden_golden.json in cwd"] = attempt(lambda: open("hidden_golden.json").read(1))
res["list home directory"] = attempt(lambda: os.listdir(os.path.expanduser("~")))
res["connect to a loopback listener"] = attempt(lambda: socket.create_connection(("127.0.0.1", port), timeout=2).close())
res["own environ contains a CANARY"] = "VISIBLE" if any("CANARY" in k or "CANARY" in v for k, v in os.environ.items()) else "not visible"
print(json.dumps(res))
'''


def strict_profile(py: str) -> str:
    real = Path(py).resolve()
    prefix = real.parent.parent
    tmp = Path(tempfile.gettempdir()).resolve()
    q = sandbox._q
    return "\n".join([
        "(version 1)", "(deny default)", '(import "bsd.sb")',
        "(allow file-read-metadata)",
        f"(allow process-exec (literal {q(py)}) (literal {q(real)}))",
        f"(allow file-read* file-map-executable (subpath {q(prefix)}) (subpath {q(REPO / '.sandboxes')}))",
        f"(allow file-read* file-write* (subpath {q(tmp)}))",
    ])


def parse(r) -> dict:
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        return {"_error": f"rc {r.returncode}: {(r.stderr or r.stdout).strip()[-200:]}"}


def report(role: str, results: dict) -> None:
    cols = list(results)
    names: list = []
    for res in results.values():
        for k in res:
            if k not in names:
                names.append(k)
    print(f"{'probe':<44}" + "".join(f" | {c:<24}" for c in cols))
    for n in names:
        print(f"{n:<44}" + "".join(f" | {str(results[c].get(n, '-')):<24}" for c in cols))
    ctrl = results.get("no profile", {})
    probes = [n for n in names if not n.startswith("_")]
    blind = [n for n in probes if ctrl.get(n) not in OPEN_VALUES]
    print("\ncontrol did NOT show these open (they say nothing about the profile):", blind or "none")
    for col in cols[1:]:
        still = [n for n in probes if ctrl.get(n) in OPEN_VALUES and results[col].get(n) in OPEN_VALUES]
        closed = [n for n in probes if ctrl.get(n) in OPEN_VALUES and results[col].get(n) not in OPEN_VALUES]
        print(f"[{col}] still open: {still or 'none'}")
        print(f"[{col}] open in control, not open here: {closed or 'none'}")


def harness(role: str) -> int:
    py = str(REPO / ".sandboxes" / "pd30" / "bin" / "python")
    cases = sorted((REPO / "benchmarks").glob("*/hidden_golden.json"))
    if not cases:
        print("no benchmark with hidden_golden.json")
        return 2
    case = cases[0].parent
    token = secrets.token_hex(6)
    env_marker = os.environ.get("CANARY_ENV_TOKEN", "CANARY_ENV_absent")
    mem_secret = "CANARY_MEM_" + token  # exists only as a Python string in this process
    cdir = Path.home() / ".config" / f"pp_canary_{os.getpid()}"
    cdir.mkdir(parents=True, exist_ok=True)
    cdir.chmod(0o700)
    cfile = cdir / "meta_key_canary"
    cfile.write_text("CANARY_FILE_" + token)
    cfile.chmod(0o600)
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)
    ws = sandbox.workspace(case, exclude=sandbox.ANSWER_KEYS + (sandbox.HIDDEN_INPUTS,))
    args = [env_marker, mem_secret, str(cfile), str(case / "hidden_golden.json"), str(srv.getsockname()[1])]
    results: dict = {}
    try:
        print(f"\n=== harness variant: {role} (fake secrets only)")
        try:
            sandbox._check_harness_env()
            print("fail-closed environment check: PASSED (initial environment looks clean)")
        except sandbox.SandboxUnavailable as e:
            print("fail-closed environment check: REFUSES model code ->", str(e)[:220])
        sandbox._ENV_CHECK = False  # measure the profile on its own
        for label, on in (("no profile", False), ("production profile", True)):
            sandbox.set_fs_deny(on)
            try:
                results[label] = parse(sandbox.run(py, ["-c", PROBE, *args], ws, timeout_s=60))
            except sandbox.SandboxUnavailable as e:
                results[label] = {"_error": "SandboxUnavailable: " + str(e)[:150]}
        r = subprocess.run(["/usr/bin/sandbox-exec", "-p", strict_profile(py), py, "-c", PROBE, *args],
                           env=sandbox.SAFE_ENV, cwd=ws, capture_output=True, text=True, timeout=120)
        results["strict default-deny"] = parse(r)
        report(role, results)
    finally:
        srv.close()
        shutil.rmtree(cdir, ignore_errors=True)
        sandbox.cleanup(ws)
    return 0


def main() -> int:
    if "--reexec-check" in sys.argv:
        sandbox.ensure_clean_env()
        print("initial environment variable names after the clean re-exec:",
              sorted(e.partition("=")[0] for e in sandbox.initial_environ()))
        return 0
    role = os.environ.get("PP_ISO_ROLE")
    if role:
        return harness(role)
    home = os.environ.get("HOME", str(Path.home()))
    for r, extra in (("env", {"CANARY_ENV_TOKEN": "CANARY_ENV_" + secrets.token_hex(6)}), ("mem", {})):
        env = {"PATH": "/usr/bin:/bin", "HOME": home, "PP_CLEAN": "1", "PP_ISO_ROLE": r, **extra}
        subprocess.run([sys.executable, "-m", "patchpilot.isolation_test"], env=env, cwd=REPO)
    print("\nnot tested: lldb/vmmap/gcore memory reads, other users' processes, other same-user processes that "
          "hold secrets in their environment, Linux, child processes started by model code")
    return 0


if __name__ == "__main__":
    sys.exit(main())
