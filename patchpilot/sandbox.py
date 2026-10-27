"""Run a command in an isolated, budgeted subprocess. Standard library only."""
from __future__ import annotations

import os
import resource
import shutil
import signal
import subprocess
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


def workspace(case_dir: str | Path) -> Path:
    """Copy a case into a fresh temp dir so the original is never modified."""
    tmp = Path(tempfile.mkdtemp(prefix="patchpilot_"))
    dst = tmp / Path(case_dir).name
    shutil.copytree(
        case_dir, dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache")
    )
    return dst


def cleanup(ws: Path) -> None:
    shutil.rmtree(ws.parent, ignore_errors=True)


def run(python: str | Path, args: list, cwd: str | Path, *, timeout_s: float = 60.0) -> RunResult:
    cmd = [os.path.abspath(str(python)), *args]
    t0 = time.monotonic()
    proc = subprocess.Popen(
        cmd,
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
