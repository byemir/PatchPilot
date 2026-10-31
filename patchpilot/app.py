"""PatchPilot in the browser: pick a manifest, check or repair, watch it live, apply a patch (standard library only).

    python -m patchpilot.app [--root DIR] [--port 8765] [--no-open]

Serves one page on 127.0.0.1. The page starts `python -m patchpilot.scan` as a subprocess for a manifest found under
--root, shows its progress events as they arrive, and can write an accepted patch into the file after you confirm.
Safety: loopback only; every API call needs the random token that was put into the page and a matching Host (and
Origin, when the browser sends one), so another web page cannot drive it; only manifests below --root can be run;
the endpoint must be a loopback address; one job at a time; a patch is written only if the file still has the exact
content (sha-256) it had when the scan read it and the accepted patch touches only that file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from patchpilot import meta_client, repair, view

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
ENDPOINT_RE = re.compile(r"^http://(127\.0\.0\.1|localhost|\[::1\]):\d{1,5}(/[A-Za-z0-9._~/-]*)?$")
HOSTED = ("muse-spark-1.3", "muse-wonder-1.0")
BASETEN = tuple(meta_client.BASETEN_MODELS)  # served by Baseten, needs its own key file
FIREWORKS = tuple(meta_client.FIREWORKS_MODELS)  # served by Fireworks, needs its own key file


def hosted_models() -> list[str]:
    """Hosted models whose key file exists."""
    return (list(HOSTED) if meta_client.KEY_PATH.exists() else []) + (list(BASETEN) if meta_client.BASETEN_KEY_PATH.exists() else []) + (list(FIREWORKS) if meta_client.FIREWORKS_KEY_PATH.exists() else [])
SKIP_DIRS = {".git", ".venv", ".sandboxes", "node_modules", "__pycache__", "runs", ".patchpilot"}
CLEAN_ENV_KEYS = ("HOME", "PATH", "TMPDIR", "LANG", "USER", "LOGNAME", "TERM")


class Job:
    def __init__(self, jid: str, manifest: str, out_dir: Path, params: dict):
        self.id, self.manifest, self.out_dir, self.params = jid, manifest, out_dir, params
        self.status = "running"
        self.events: list[dict] = []
        self.rows: list[dict] = []
        self.proc = None
        self.lock = threading.Lock()
        self.started = time.time()

    def add(self, ev: dict) -> None:
        with self.lock:
            k = ev.get("index")
            if ev["event"] == "start":
                self.rows = [dict() for _ in range(ev["total"])]
            elif ev["event"] in ("triage", "result"):
                self.rows[k].update(ev["row"])
            elif ev["event"] == "applied":
                self.rows[k]["applied"] = True
            elif ev["event"] == "undone":
                self.rows[k]["applied"] = False
            self.events.append(ev)

    def since(self, n: int) -> dict:
        def clean(ev):  # absolute paths and hashes stay on the server
            if "row" in ev:
                ev = {**ev, "row": {k: v for k, v in ev["row"].items() if k not in ("path", "run_dir", "source_sha256")}}
            return ev
        with self.lock:
            return {"id": self.id, "status": self.status, "manifest": self.manifest, "n": len(self.events),
                    "events": [clean(e) for e in self.events[max(n, 0):]], "params": self.params}


def subprocess_runner(argv: list[str], on_line, holder: dict) -> int:
    env = {k: os.environ[k] for k in CLEAN_ENV_KEYS if k in os.environ}
    py = REPO / ".venv" / "bin" / "python"  # the interpreter the tests use, when the repository has one
    p = subprocess.Popen([str(py) if py.exists() else sys.executable, "-m", "patchpilot.scan", *argv], cwd=REPO, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, start_new_session=True)
    holder["proc"] = p
    err: list[str] = []
    t = threading.Thread(target=lambda: err.append(p.stderr.read()), daemon=True)
    t.start()
    for line in p.stdout:
        on_line(line)
    p.wait()
    t.join(2)
    holder["stderr"] = "".join(err)[-800:]
    return p.returncode


class App:
    def __init__(self, root: Path, runner=subprocess_runner):
        self.root = root.resolve()
        self.token = secrets.token_urlsafe(24)
        self.runner = runner
        self.job: Job | None = None
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.port = 0

    # ---- discovery
    def manifests(self) -> list[str]:
        out = []
        for dp, dirs, files in os.walk(self.root):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
            if Path(dp).relative_to(self.root).parts.__len__() > 4:
                dirs[:] = []
            for f in files:
                if not f.endswith(".json"):
                    continue
                p = Path(dp) / f
                try:
                    if p.stat().st_size > 200_000:
                        continue
                    d = json.loads(p.read_text())
                    if isinstance(d, dict) and isinstance(d.get("targets"), list) and d["targets"] and all(
                            isinstance(t, dict) and {"file", "function", "lib", "inputs"} <= set(t) for t in d["targets"]):
                        out.append(str(p.relative_to(self.root)))
                except (OSError, ValueError):
                    continue
        return sorted(out)

    def previous(self) -> list[dict]:
        base = self.root / ".patchpilot"
        res = []
        if base.is_dir():
            for d in sorted(base.iterdir(), reverse=True)[:20]:
                if (d / "scan_report.json").is_file():
                    res.append({"id": d.name})
        return res

    def state(self) -> dict:
        return {"root": self.root.name, "manifests": self.manifests(), "hosted": hosted_models(),
                "endpoint": "http://127.0.0.1:8080/v1", "previous": self.previous(),
                "changed": self.changed(), "envs": all(Path(repair.default_python(l, k)).exists() for l in repair.ENVS for k in (0, 1)), "job": self.job.since(0)["status"] if self.job else None}

    def health(self, endpoint: str) -> dict:
        if not ENDPOINT_RE.match(endpoint):
            return {"ok": False, "reason": "not a loopback address"}
        url = re.sub(r"/v1/?$", "", endpoint.rstrip("/")) + "/health"
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                return {"ok": r.status == 200}
        except Exception:
            return {"ok": False, "reason": "no server"}

    # ---- jobs
    def start(self, p: dict) -> tuple[int, dict]:
        with self.lock:
            if self.job and self.job.status == "running":
                return 409, {"error": "a job is already running"}
            rel = p.get("manifest")
            if rel not in self.manifests():
                return 400, {"error": "unknown manifest"}
            mode = p.get("mode")
            if mode not in ("check", "repair"):
                return 400, {"error": "mode must be check or repair"}
            effort, attempts = p.get("effort", "low"), p.get("max_attempts", 3)
            if effort not in ("low", "medium") or not isinstance(attempts, int) or not 1 <= attempts <= 5:
                return 400, {"error": "bad effort or attempts"}
            only = p.get("only")
            argv_only: list[str] = []
            if only is not None:
                try:
                    n_targets = len(json.loads((self.root / rel).read_text())["targets"])
                except (OSError, ValueError, KeyError):
                    return 400, {"error": "unreadable manifest"}
                if (not isinstance(only, list) or not only or len(only) > n_targets
                        or not all(isinstance(i, int) and not isinstance(i, bool) and 0 <= i < n_targets for i in only)):
                    return 400, {"error": "bad row selection"}
                argv_only = ["--only", ",".join(str(i) for i in sorted(set(only)))]
            argv_model: list[str] = []
            if mode == "repair":
                if p.get("model") == "local":
                    ep = p.get("endpoint", "")
                    if not isinstance(ep, str) or not ENDPOINT_RE.match(ep):
                        return 400, {"error": "the endpoint must be a loopback address"}
                    argv_model = ["--endpoint", ep]
                elif p.get("model") in hosted_models():
                    argv_model = ["--model", p["model"]]
                else:
                    return 400, {"error": "unknown model"}
            stamp = time.time()
            while True:  # one folder per run, even when two runs start in the same second
                jid = time.strftime("%Y%m%d-%H%M%S", time.localtime(stamp))
                out = self.root / ".patchpilot" / jid
                if not out.exists():
                    break
                stamp += 1
            out.mkdir(parents=True)
            job = Job(jid, rel, out, {k: p.get(k) for k in ("mode", "model", "effort", "max_attempts")})
            self.job = job
            self.jobs[jid] = job
        argv = [str(self.root / rel), "--events", "--out-dir", str(out), "--runs-dir", str(out / "runs"), "--effort", effort,
                "--max-attempts", str(attempts), *argv_model, *argv_only] + (["--triage-only"] if mode == "check" else [])
        threading.Thread(target=self._run, args=(job, argv), daemon=True).start()
        return 200, {"id": jid}

    def _run(self, job: Job, argv: list[str]) -> None:
        holder: dict = {}
        job.proc = holder

        def on_line(line: str) -> None:
            try:
                ev = json.loads(line)
                if isinstance(ev, dict) and "event" in ev:
                    job.add(ev)
            except ValueError:
                pass
        print(f"job {job.id}: started ({job.params.get('mode')}, {job.params.get('model')})", flush=True)
        try:
            rc = self.runner(argv, on_line, holder)
        except Exception as e:  # runner could not start
            rc, holder["stderr"] = 2, f"{type(e).__name__}: {e}"
        print(f"job {job.id}: ended, exit code {rc}, {len(job.events)} events" + (f"\n  {holder['stderr'].strip()[-400:]}" if holder.get("stderr", "").strip() else ""), flush=True)
        try:
            (job.out_dir / "job.log").write_text(f"exit code {rc}\n{holder.get('stderr', '')}")
        except OSError:
            pass
        with job.lock:
            stopped = job.status == "stopping"
        if stopped:
            job.add({"event": "stopped"})
        elif rc not in (0, 1):
            job.add({"event": "error", "message": (holder.get("stderr") or "the scan could not run").strip()[-300:]})
        with job.lock:
            job.status = "stopped" if stopped else ("failed" if rc not in (0, 1) else "done")

    def stop(self) -> tuple[int, dict]:
        job = self.job
        if not job or job.status != "running":
            return 409, {"error": "no running job"}
        with job.lock:
            job.status = "stopping"
        proc = (job.proc or {}).get("proc")
        if proc:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
        return 200, {"ok": True}

    # ---- baseline: the first content of every file the app wrote, so Reset can put the whole folder back
    def _bl(self) -> Path:
        return self.root / ".patchpilot" / "baseline"

    def _bl_load(self) -> dict:
        try:
            d = json.loads((self._bl() / "index.json").read_text())
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def _bl_save(self, idx: dict) -> None:
        b = self._bl()
        b.mkdir(parents=True, exist_ok=True)
        t = b / "index.json.tmp"
        t.write_text(json.dumps(idx))
        os.replace(t, b / "index.json")

    def _bl_before(self, src: Path) -> None:  # call before the app writes src
        rel = str(src.relative_to(self.root))
        idx = self._bl_load()
        now = hashlib.sha256(src.read_bytes()).hexdigest()
        if rel not in idx or idx[rel].get("written") != now:  # first write, or the file was changed by hand since: start over from here
            bf = self._bl() / "files" / rel
            bf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, bf)
            idx[rel] = {"orig": now, "written": now}
            self._bl_save(idx)

    def _bl_after(self, src: Path) -> None:  # call after the app wrote src
        rel = str(src.relative_to(self.root))
        idx = self._bl_load()
        if rel in idx:
            idx[rel]["written"] = hashlib.sha256(src.read_bytes()).hexdigest()
            self._bl_save(idx)

    def changed(self) -> int:
        n = 0
        for rel, e in self._bl_load().items():
            try:
                if hashlib.sha256((self.root / rel).read_bytes()).hexdigest() != e.get("orig"):
                    n += 1
            except OSError:
                n += 1
        return n

    def reset(self) -> tuple[int, dict]:
        if self.job and self.job.status in ("running", "stopping"):
            return 409, {"error": "a run is in progress"}
        idx = self._bl_load()
        restored, skipped, back = 0, [], set()
        for rel, e in list(idx.items()):
            try:
                src = (self.root / rel).resolve()
                src.relative_to(self.root)
                files = (self._bl() / "files").resolve()
                bf = (files / rel).resolve()
                bf.relative_to(files)
                cur = hashlib.sha256(src.read_bytes()).hexdigest() if src.exists() else None
                if cur == e.get("orig"):
                    del idx[rel]
                    continue
                if cur != e.get("written") or hashlib.sha256(bf.read_bytes()).hexdigest() != e.get("orig"):
                    skipped.append(rel)  # edited by hand since the app wrote it, or the saved copy is damaged: leave it alone
                    continue
                tmp = src.with_name(src.name + ".patchpilot.tmp")
                shutil.copy2(bf, tmp)
                os.replace(tmp, src)
                back.add(str(src))
                restored += 1
                del idx[rel]
            except (OSError, ValueError, KeyError):
                skipped.append(rel)
        self._bl_save(idx)
        for job in list(self.jobs.values()):
            for k, row in enumerate(job.rows):
                if row.get("applied") and row.get("path") and str(Path(row["path"]).resolve()) in back:
                    job.add({"event": "undone", "index": k})
        return 200, {"ok": True, "restored": restored, "skipped": skipped}

    def _find(self, index, jid):
        job = self.jobs.get(jid) if isinstance(jid, str) else self.job
        if not job or not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(job.rows):
            return None, None
        return job, job.rows[index]

    def apply(self, index, jid=None) -> tuple[int, dict]:
        job, row = self._find(index, jid)
        if job is None:
            return 400, {"error": "unknown function"}
        if row.get("status") != "repaired" or row.get("applied"):
            return 409, {"error": "nothing to apply"}
        try:
            src = Path(row["path"]).resolve()
            src.relative_to(self.root)
            run = Path(row["run_dir"]).resolve()
            run.relative_to(job.out_dir.resolve())
            last = json.loads((run / f"attempt_{row['attempts']}.json").read_text())
            files = last.get("files") or {}
            current = src.read_text()
            if set(files) != {"app.py"}:
                return 409, {"error": "the patch touches more than one file; apply the diff by hand"}
            if hashlib.sha256(src.read_bytes()).hexdigest() != row.get("source_sha256"):
                return 409, {"error": "the file changed since the scan; run it again"}
            backup = job.out_dir / "backup" / f"{index}.orig"  # the original, so Undo can put it back
            backup.parent.mkdir(exist_ok=True)
            shutil.copy2(src, backup)
            self._bl_before(src)
            repair.apply_patch(src, current, files["app.py"])
            self._bl_after(src)
            row["backup"] = str(backup)
            row["applied_sha"] = hashlib.sha256(src.read_bytes()).hexdigest()
        except (KeyError, ValueError, OSError, RuntimeError) as e:
            return 409, {"error": f"not applied: {e}"}
        job.add({"event": "applied", "index": index})
        return 200, {"ok": True}

    def undo(self, index, jid=None) -> tuple[int, dict]:
        job, row = self._find(index, jid)
        if job is None:
            return 400, {"error": "unknown function"}
        if not row.get("applied") or not row.get("backup"):
            return 409, {"error": "nothing to undo"}
        try:
            src = Path(row["path"]).resolve()
            src.relative_to(self.root)
            backup = Path(row["backup"])
            backup.resolve().relative_to(job.out_dir.resolve())
            if hashlib.sha256(src.read_bytes()).hexdigest() != row.get("applied_sha"):
                return 409, {"error": "the file was edited after Apply; not restoring over your changes"}
            tmp = src.with_name(src.name + ".patchpilot.tmp")
            shutil.copy2(backup, tmp)
            os.replace(tmp, src)
            self._bl_after(src)
        except (KeyError, ValueError, OSError) as e:
            return 409, {"error": f"not restored: {e}"}
        job.add({"event": "undone", "index": index})
        return 200, {"ok": True}

    def report(self, rid: str) -> tuple[int, dict]:
        if not re.fullmatch(r"[0-9]{8}-[0-9]{6}", rid or ""):
            return 400, {"error": "bad id"}
        p = self.root / ".patchpilot" / rid / "scan_report.json"
        if not p.is_file():
            return 404, {"error": "not found"}

        class A:  # reuse the static viewer's builder
            report, run, runs_root = str(p), None, str(p.parent / "runs")
        return 200, view.build(A)


def make_handler(app: App):
    page = (HERE / "app.html").read_text()
    page = page.replace("</head>", f'<meta name="pp-token" content="{app.token}">\n</head>', 1).encode()

    class H(BaseHTTPRequestHandler):
        def _ok(self) -> bool:
            host = self.headers.get("Host", "")
            allowed = {f"127.0.0.1:{app.port}", f"localhost:{app.port}"}
            origin = self.headers.get("Origin")
            if host not in allowed or (origin is not None and origin not in {f"http://{h}" for h in allowed}):
                self.send_error(403)
                return False
            return True

        def _json(self, code: int, obj) -> None:
            body = json.dumps(view.finite(obj), allow_nan=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _authed(self) -> bool:
            if not secrets.compare_digest(self.headers.get("X-PatchPilot-Token", ""), app.token):
                self._json(403, {"error": "missing or wrong token"})
                return False
            return True

        def do_GET(self):
            if not self._ok():
                return
            path, _, query = self.path.partition("?")
            if path in ("/", "/index.html"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(page)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(page)
                return
            if not path.startswith("/api/"):
                self.send_error(404)
                return
            if not self._authed():
                return
            q = dict(kv.split("=", 1) for kv in query.split("&") if "=" in kv)
            if path == "/api/state":
                self._json(200, app.state())
            elif path == "/api/job":
                job = app.job
                self._json(200, job.since(int(q.get("since", "0") or 0)) if job else {"status": None, "events": [], "n": 0})
            elif path == "/api/health":
                self._json(200, app.health(urllib.parse.unquote(q.get("endpoint", ""))))
            elif path == "/api/report":
                self._json(*app.report(q.get("id", "")))
            else:
                self.send_error(404)

        def do_POST(self):
            if not self._ok() or not self._authed():
                return
            try:
                n = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(min(n, 20_000)) or b"{}")
                assert isinstance(body, dict)
            except (ValueError, AssertionError):
                self._json(400, {"error": "bad request"})
                return
            if self.path == "/api/run":
                self._json(*app.start(body))
            elif self.path == "/api/stop":
                self._json(*app.stop())
            elif self.path == "/api/apply":
                self._json(*app.apply(body.get("index"), body.get("job")))
            elif self.path == "/api/reset":
                self._json(*app.reset())
            elif self.path == "/api/undo":
                self._json(*app.undo(body.get("index"), body.get("job")))
            else:
                self.send_error(404)

        def log_message(self, *a):
            pass

    return H


def serve(root: Path, port: int, runner=subprocess_runner) -> tuple[App, ThreadingHTTPServer]:
    app = App(root, runner)
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    app.port = srv.server_address[1]
    return app, srv


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="PatchPilot in the browser.")
    ap.add_argument("--root", default=".", help="folder to look for scan manifests in (default: here)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root)
    if not root.is_dir():
        print(f"app: {root} is not a folder", file=sys.stderr)
        return 2
    app, srv = serve(root, a.port)
    url = f"http://127.0.0.1:{app.port}"
    print(f"PatchPilot at {url}   (folder: {app.root}; Ctrl+C to stop)")
    if not a.no_open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        if app.job and app.job.status == "running":
            app.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
