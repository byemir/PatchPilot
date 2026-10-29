"""Run a command in an isolated, budgeted subprocess. Standard library only.

File-system and network isolation of model code: macOS uses sandbox-exec (a deny list for the home directory and the
repository); Linux uses Landlock through patchpilot/landlock_exec.py (an allow list: the workspace, the interpreter and
system libraries). On other platforms model code is not run unless isolation is switched off explicitly."""
from __future__ import annotations

import json
import os
import platform
import re
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

# Minimal, deterministic environment: no inherited secrets, fixed timezone and hash seed.
SAFE_ENV = {
    "PATH": "/usr/bin:/bin",
    "TZ": "UTC",
    "PYTHONHASHSEED": "0",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONUTF8": "1",
}
MAX_OUTPUT = 200_000


@dataclass
class RunResult:
    cmd: list
    returncode: int | None
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _limits(cpu_s: int):
    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_s, cpu_s))

    return apply


# Files that patched code must never see: expected outputs and reference patches.
ANSWER_KEYS = ("golden.json", "hidden_golden.json", "known_good.json", "known_bad")
HIDDEN_INPUTS = "hidden_inputs.json"


def workspace(case_dir: str | Path, exclude: tuple = ()) -> Path:
    """Copy a case into a fresh temp dir so the original is never modified.

    `exclude` lists file or directory names that are not copied (matched anywhere in the tree).
    """
    tmp = Path(tempfile.mkdtemp(prefix="patchpilot_"))
    dst = tmp / Path(case_dir).name
    shutil.copytree(
        case_dir, dst,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", *exclude),
    )
    return dst


def cleanup(ws: Path) -> None:
    shutil.rmtree(ws.parent, ignore_errors=True)


SANDBOX_EXEC = "/usr/bin/sandbox-exec"
FS_DENY = True  # fail-closed default; only an explicit --no-fs-deny turns it off (such runs are not counted)
_SELFTESTED: set = set()


class SandboxUnavailable(RuntimeError):
    pass


def set_fs_deny(enabled: bool) -> None:
    global FS_DENY
    FS_DENY = bool(enabled)


def _q(path) -> str:
    return '"' + str(path).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _repo() -> Path:
    return Path(__file__).resolve().parents[1]


def profile_for(python, extra: str = "") -> str:
    """macOS Seatbelt profile: no access to the home directory or the repository (hidden files, keys),
    except read access to the sandbox environments and the interpreter installation; no network."""
    home, repo = Path.home().resolve(), _repo()
    rules = ["(version 1)", "(allow default)",
             f"(deny file-read* file-write* (subpath {_q(home)}))",
             f"(deny file-read* file-write* (subpath {_q(repo)}))",
             f"(allow file-read* (subpath {_q(repo / '.sandboxes')}))"]
    prefix = Path(python).resolve().parent.parent
    if home in prefix.parents:
        rules.append(f"(allow file-read* (subpath {_q(prefix)}))")
    rules.append("(deny network*)")
    if extra:
        rules.append(extra)
    return "\n".join(rules)


_SELFTEST_CODE = '''
import errno, json, os, socket, sys
home, canary, wpath = sys.argv[1:4]

def t(fn):
    try:
        fn()
        return "allowed"
    except PermissionError:
        return "denied"
    except OSError as e:  # network namespace without a route: no way out either
        if e.errno in (errno.ENETUNREACH, errno.ENETDOWN, errno.EADDRNOTAVAIL):
            return "denied"
        return "other:" + type(e).__name__
    except Exception as e:
        return "other:" + type(e).__name__

def w():
    open(wpath, "x").close()

print(json.dumps({"read_repo_file": t(lambda: open(canary).read(1)),
                  "list_home": t(lambda: os.listdir(home)),
                  "write_home": t(w),
                  "network": t(lambda: socket.create_connection(("127.0.0.1", 9), timeout=1))}))
'''


def _selftest(python: str, prof: str) -> None:
    home, repo = Path.home().resolve(), _repo()
    canary = (sorted((repo / "benchmarks").glob("*/hidden_golden.json")) or [repo / "README.md"])[0]
    wpath = home / f".pp_selftest_{os.getpid()}"
    try:
        r = subprocess.run([SANDBOX_EXEC, "-p", prof, python, "-c", _SELFTEST_CODE, str(home), str(canary), str(wpath)],
                           env=SAFE_ENV, capture_output=True, text=True, timeout=60, cwd=tempfile.gettempdir())
    finally:
        wpath.unlink(missing_ok=True)  # exists only if the write was NOT denied
    try:
        res = json.loads(r.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        raise SandboxUnavailable(f"sandbox self-test did not run: {r.stderr[-300:]}") from None
    bad = {k: v for k, v in res.items() if v != "denied"}
    if bad:
        raise SandboxUnavailable(f"sandbox self-test: access was not denied for {bad}")


LAUNCHER = Path(__file__).with_name("landlock_exec.py")
LINUX_NETNS = True  # try an empty network namespace on top of Landlock; the launcher continues without it if the kernel refuses
LINUX_INFO: dict = {}  # filled by the self-test: {"abi": ..., "netns": ...}
_LINUX_SYSTEM_RO = ("/usr", "/lib", "/lib64", "/bin", "/sbin", "/etc/ld.so.cache", "/etc/ld.so.conf", "/etc/ld.so.conf.d",
                    "/etc/localtime", "/etc/nsswitch.conf", "/etc/passwd", "/etc/group", "/proc/cpuinfo", "/proc/meminfo",
                    "/sys/devices/system/cpu")


def linux_ro_paths(python) -> list:
    """Read-only roots for the interpreter: system directories, the environment of this interpreter and the
    installation its pyvenv.cfg points to. Never the home directory or the filesystem root itself."""
    home = Path.home().resolve()
    paths = list(_LINUX_SYSTEM_RO)
    p = Path(python)
    roots = {p.parent.parent, p.resolve().parent.parent}
    cfg = p.parent.parent / "pyvenv.cfg"
    if cfg.exists():
        for line in cfg.read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip() == "home" and v.strip():
                roots.add(Path(v.strip()).resolve().parent)
    for r in roots:
        if r not in (Path("/"), home):
            paths.append(str(r))
    return paths


def linux_wrap(cmd: list, cwd) -> list:
    out = [sys.executable, "-I", "-S", str(LAUNCHER)]
    if LINUX_NETNS:
        out.append("--netns")
    for q in linux_ro_paths(cmd[0]):
        out += ["--ro", q]
    out += ["--rw", str(Path(cwd).resolve()), "--rw", "/dev/null", "--"]
    return out + cmd


def _selftest_linux(python: str) -> None:
    home, repo = Path.home().resolve(), _repo()
    canary = (sorted((repo / "benchmarks").glob("*/hidden_golden.json")) or [repo / "README.md"])[0]
    work = Path(tempfile.mkdtemp(prefix="pp_selftest_"))
    wpath = home / f".pp_selftest_{os.getpid()}"
    try:
        cmd = linux_wrap([os.path.abspath(python), "-c", _SELFTEST_CODE, str(home), str(canary), str(wpath)], work)
        cmd.insert(4, "--report")
        r = subprocess.run(cmd, env=SAFE_ENV, capture_output=True, text=True, timeout=60, cwd=work)
    finally:
        wpath.unlink(missing_ok=True)  # exists only if the write was NOT denied
        shutil.rmtree(work, ignore_errors=True)
    if r.returncode == 126:
        raise SandboxUnavailable("Landlock is not available here (" + r.stderr.strip()[-200:] + "); model code is not run "
                                 "without file-system isolation (--no-fs-deny runs it unisolated; such runs are not counted)")
    try:
        res = json.loads(r.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        raise SandboxUnavailable(f"sandbox self-test did not run: {r.stderr[-300:]}") from None
    bad = {k: v for k, v in res.items() if v != "denied"}
    if bad:
        raise SandboxUnavailable(f"sandbox self-test: access was not denied for {bad}")
    for part in r.stderr.split():
        if part.startswith(("abi=", "netns=")):
            k, _, v = part.partition("=")
            LINUX_INFO[k] = int(v)


EXTRA_RULES = ""  # extra Seatbelt rules appended to the profile; none has been shown to help so far
_ENV_CHECK = True  # tests may switch the check off to measure the profile alone
_KEEP_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "TERM", "USER", "LOGNAME", "PP_CLEAN")
_SUSPECT_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSW|CREDENTIAL|AUTH|CANARY", re.I)
_KEYLIKE = re.compile(r"[A-Za-z0-9_\-]{32,}|sk-[A-Za-z0-9_\-]{16,}")


def initial_environ() -> list:
    """Entries 'NAME=value' of this process's INITIAL environment, read the way other same-user code could
    read it (sysctl KERN_PROCARGS2). Falls back to os.environ when that is not possible."""
    if sys.platform.startswith("linux"):
        try:
            return [x.decode("utf-8", "replace") for x in Path("/proc/self/environ").read_bytes().split(b"\0") if x]
        except OSError:
            pass
    try:
        import ctypes
        import ctypes.util

        libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
        mib = (ctypes.c_int * 3)(1, 49, os.getpid())
        size = ctypes.c_size_t(0)
        if libc.sysctl(mib, 3, None, ctypes.byref(size), None, 0) != 0:
            raise OSError("sysctl size query failed")
        buf = ctypes.create_string_buffer(size.value)
        if libc.sysctl(mib, 3, buf, ctypes.byref(size), None, 0) != 0:
            raise OSError("sysctl read failed")
        data = buf.raw[: size.value]
        argc = int.from_bytes(data[:4], "little")
        i = data.index(b"\0", 4) + 1
        while i < len(data) and data[i] == 0:
            i += 1
        for _ in range(argc):
            i = data.index(b"\0", i) + 1
        env = []
        while i < len(data) and data[i] != 0:
            j = data.index(b"\0", i)
            env.append(data[i:j].decode("utf-8", "replace"))
            i = j + 1
        return env
    except Exception:
        return [f"{k}={v}" for k, v in os.environ.items()]


def _check_harness_env() -> None:
    """Fail closed: model code can read this process's initial environment, so refuse to run it while
    secret-looking variables (by name or by key-shaped value) are in it. Only names are reported."""
    if not _ENV_CHECK:
        return
    bad = set()
    for entry in initial_environ() + [f"{k}={v}" for k, v in os.environ.items()]:
        name, _, value = entry.partition("=")
        if _SUSPECT_NAME.search(name) or _KEYLIKE.fullmatch(value.strip()):
            bad.add(name)
    if bad:
        raise SandboxUnavailable(
            "the harness environment holds secret-looking variables (" + ", ".join(sorted(bad)) + "); model code "
            "could read them, so it is not run. Start through bench/agent (clean re-exec) or unset them.")


def ensure_clean_env() -> None:
    """Re-exec this process with a minimal environment so that nothing exported in the shell is in its
    initial environment."""
    if os.environ.get("PP_CLEAN") == "1" or not getattr(sys, "orig_argv", None):
        return
    env = {k: os.environ[k] for k in _KEEP_ENV if k in os.environ}
    env["PP_CLEAN"] = "1"
    os.execve(sys.executable, [sys.executable, *sys.orig_argv[1:]], env)


def _wrap(cmd: list, cwd=None) -> list:
    if not FS_DENY:
        return cmd
    _check_harness_env()
    python = cmd[0]
    if platform.system() == "Linux":
        if python not in _SELFTESTED:
            _selftest_linux(python)
            _SELFTESTED.add(python)
        return linux_wrap(cmd, cwd if cwd is not None else os.getcwd())
    if platform.system() != "Darwin" or not os.path.exists(SANDBOX_EXEC):
        raise SandboxUnavailable("sandbox-exec is not available; model code is not run without file-system "
                                 "isolation (--no-fs-deny runs it unisolated; such runs are not counted)")
    prof = profile_for(python, EXTRA_RULES)
    if python not in _SELFTESTED:
        _selftest(python, prof)
        _SELFTESTED.add(python)
    return [SANDBOX_EXEC, "-p", prof, *cmd]


def run(python: str | Path, args: list, cwd: str | Path, *, timeout_s: float = 60.0) -> RunResult:
    cmd = [os.path.abspath(str(python)), *args]
    t0 = time.monotonic()
    proc = subprocess.Popen(
        _wrap(cmd, cwd),
        cwd=str(cwd),
        env=SAFE_ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        preexec_fn=_limits(int(timeout_s) + 5),
    )
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGKILL)
        out, err = proc.communicate()
    return RunResult(
        cmd=cmd,
        returncode=None if timed_out else proc.returncode,
        stdout=out[:MAX_OUTPUT],
        stderr=err[:MAX_OUTPUT],
        duration_s=round(time.monotonic() - t0, 3),
        timed_out=timed_out,
    )
