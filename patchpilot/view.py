"""Browser view of a scan report or of one recorded run (standard library only; no network beyond 127.0.0.1).

    python -m patchpilot.view scan_out/scan_report.json            # a report written by patchpilot.scan
    python -m patchpilot.view --run runs/20261029-213446_q3_scalar_repr   # one recorded run, attempt by attempt

Opens http://127.0.0.1:8765 . The server only reads the files named at start and the attempt records of the runs in the
report; it changes nothing. The page replays each attempt through the three gates.
"""
from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent


def gates_of(rec: dict) -> dict:
    """Per-gate outcome of one attempt record: ok, fail, skipped, off or n/a."""
    if "error" in rec and "old_verdict" not in rec:
        return {"visible": "skipped", "hidden": "skipped", "differential": "skipped", "outcome": "invalid reply"}
    vis = rec.get("old_verdict") == "OK" and rec.get("new_verdict") == "OK"
    out = {"visible": "ok" if vis else "fail"}
    if not vis:
        out.update(hidden="skipped", differential="skipped", outcome="rejected at the visible tests")
        return out
    if rec.get("hidden_old") is None:
        out["hidden"] = "n/a"
        hid = True
    else:
        hid = rec.get("hidden_old") == "OK" and rec.get("hidden_new") == "OK"
        out["hidden"] = "ok" if hid else "fail"
    if not hid:
        out.update(differential="skipped", outcome="rejected at the hidden tests")
        return out
    dv = rec.get("differential")
    if dv is None:
        out.update(differential="off", outcome="accepted" if rec.get("success") else "not accepted")
        return out
    ok = dv.get("verdict") in ("PASS", "WEAK")
    out["differential"] = "ok" if ok else "fail"
    out["outcome"] = "accepted" if ok else "rejected at the differential check"
    return out


def attempt_view(rec: dict) -> dict:
    g = gates_of(rec)
    dv = rec.get("differential") or {}
    ex = next((e for e in dv.get("examples", []) if e.get("tier") == "core"), None)
    return {"attempt": rec.get("attempt"), "gates": g, "diagnosis": rec.get("diagnosis") or rec.get("error"),
            "tokens": (rec.get("usage") or {}).get("total_tokens"),
            "differential": {k: dv.get(k) for k in ("verdict", "generated", "valid", "core_divergences")} if dv else None,
            "counterexample": ex and {"input": ex.get("probe"), "expected": ex.get("expected"), "got": ex.get("got"),
                                      "where": ex.get("where")}}


def run_view(run_dir: Path) -> dict:
    atts = [attempt_view(json.loads(p.read_text())) for p in sorted(run_dir.glob("attempt_*.json"),
                                                                    key=lambda p: int(p.stem.split("_")[1]))]
    patch = run_dir / "patch.diff"
    return {"attempts": atts, "diff": patch.read_text() if patch.exists() else None}


def build(args) -> dict:
    if args.run:
        d = Path(args.run)
        r = run_view(d)
        row = {"file": d.name, "function": "", "lib": "", "status": "repaired" if r["diff"] else "not_repaired",
               "detail": "one recorded run", "example": None, **r}
        return {"title": d.name, "summary": {}, "targets": [row]}
    rep = json.loads(Path(args.report).read_text())
    allowed_root = Path(args.runs_root).resolve() if args.runs_root else None
    rows = []
    for t in rep["targets"]:
        row = {k: t.get(k) for k in ("file", "function", "lib", "status", "detail", "example", "attempts", "tokens",
                                     "seconds", "diagnosis", "differential", "applied")}
        rd = t.get("run_dir")
        if rd and (allowed_root is None or Path(rd).resolve().is_relative_to(allowed_root)) and Path(rd).is_dir():
            row.update(run_view(Path(rd)))
        df = t.get("diff_file")
        if df and (Path(args.report).parent / df).is_file():
            row["diff"] = (Path(args.report).parent / df).read_text()
        rows.append(row)
    summary = {k: rep.get(k) for k in ("model", "endpoint", "effort", "seconds", "tokens", "counts", "triage_only")}
    return {"title": "PatchPilot scan", "summary": summary, "targets": rows}


def make_handler(data: dict):
    page = (HERE / "view.html").read_bytes()
    payload = json.dumps(data).encode()

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ("/", "/index.html"):
                body, ctype = page, "text/html; charset=utf-8"
            elif self.path == "/api/data":
                body, ctype = payload, "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    return H


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Browser view of a PatchPilot scan report or run.")
    ap.add_argument("report", nargs="?", help="scan_report.json written by patchpilot.scan")
    ap.add_argument("--run", help="a single run folder (runs/...) instead of a report")
    ap.add_argument("--runs-root", help="only read run folders below this path (default: any path named in the report)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true", help="do not open the browser")
    a = ap.parse_args(argv)
    if bool(a.report) == bool(a.run):
        print("view: give either a scan_report.json or --run RUN_DIR", file=sys.stderr)
        return 2
    src = Path(a.report or a.run)
    if not src.exists():
        print(f"view: {src} not found", file=sys.stderr)
        return 2
    data = build(a)
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(data))
    url = f"http://127.0.0.1:{a.port}"
    print(f"serving {src} at {url}  (Ctrl+C to stop)")
    if not a.no_open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
