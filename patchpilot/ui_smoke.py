"""Optional browser check of the app page (needs Playwright and a Chromium; skips itself without them).
Run: python -m patchpilot.ui_smoke   It plays one repaired function with a scripted runner (no model) and clicks through:
Repair, Auto-apply, a manual write, Reset, Auto-write with its animation states, and the row that opens by itself."""
from __future__ import annotations

import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

from patchpilot import app as appmod, app_test as T


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("skip  ui_smoke (Playwright is not installed; it is not needed to run PatchPilot)")
        return 0
    tmp = Path(tempfile.mkdtemp())
    fails: list[str] = []

    def check(name, ok):
        print(("ok   " if ok else "FAIL ") + name)
        if not ok:
            fails.append(name)
    try:
        root = tmp / "root"
        root.mkdir()
        src = T.project(root) / "mod.py"
        orig = src.read_text()
        app, srv = appmod.serve(root, 0)
        app.runner = T.fake_runner(src, {"app.py": "def f(x):\n    return x + 0\n"})
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        with sync_playwright() as p:
            try:
                b = p.chromium.launch()
            except Exception as e:  # no browser installed
                print(f"skip  ui_smoke (no Chromium: {str(e).splitlines()[0]})")
                return 0
            pg = b.new_page(viewport={"width": 1280, "height": 800})
            errs: list[str] = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://127.0.0.1:{app.port}/")
            pg.wait_for_selector("#reset")
            check("Reset is disabled before anything was written", pg.is_disabled("#reset"))
            pg.click("#mode button:has-text('Repair')")
            pg.click("#auto button:has-text('Auto-apply')")
            pg.click("#run")
            pg.wait_for_selector("tr.row button:has-text('Write file?')", timeout=15000)
            check("Auto-apply arms the button and writes nothing", src.read_text() == orig)
            check("the fixed row opens by itself", pg.locator("tr.detail").count() == 1)
            check("the fixed row shows its patch", "Patch" in pg.inner_text("tr.detail"))
            pg.click("tr.row button:has-text('Write file?')")
            pg.wait_for_selector("text=written", timeout=5000)
            check("a manual confirm writes the patch", src.read_text() != orig)
            pg.wait_for_selector("#reset:not([disabled])", timeout=5000)
            pg.click("#reset")
            check("Reset asks once more", "Reset files?" in pg.inner_text("#reset"))
            pg.click("#reset")
            pg.wait_for_selector("tr.row button:has-text('Apply')", timeout=5000)
            check("Reset restores the file", src.read_text() == orig)
            pg.click("#auto button:has-text('Auto-write')")
            check("Auto-write switches Auto-apply on", pg.get_attribute("#auto button:has-text('Auto-apply')", "aria-pressed") == "true")
            pg.click("#run")
            seen: list[str] = []
            t0 = time.time()
            while time.time() - t0 < 10:
                t = pg.inner_text("tr.row td:last-child")
                if not seen or seen[-1] != t:
                    seen.append(t)
                if "written" in t and "Undo" in t:
                    break
                pg.wait_for_timeout(100)
            check("Auto-write shows Write file?, Writing and written by itself", any("Write file?" in t for t in seen) and any("Writing" in t for t in seen) and "written" in seen[-1])
            check("the file was written", src.read_text() != orig)
            pg.click("#reset")
            pg.click("#reset")
            pg.wait_for_timeout(800)
            check("Reset restores the file again", src.read_text() == orig)
            check("no script errors on the page", not errs)
            b.close()
        srv.shutdown()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"ui_smoke: {'all checks passed' if not fails else str(len(fails)) + ' FAILED'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
