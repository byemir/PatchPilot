#!/usr/bin/env python3
"""Make function-scoped copies of the third-party cases: the vendored function stays in app.py (editable), the adapter moves to
tests/adapter.py (read-only for the agent, see PROTECTED in patchpilot/agent.py). Inputs and golden files are unchanged.
First exports the earlier unscoped runs (runs/ is not tracked) to docs/real_cases/results_unscoped_20261029.json."""
import ast, glob, json, os, re, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; os.chdir(ROOT)
MARK = "\n\n\n# --- adapter (ours) ---\n"
OLD_LINE = 'Everything under the marker "adapter (ours)" was written for this project.\n'
NEW_LINE = 'The adapter (ours) is in tests/adapter.py and is read-only for the repair.\n'
PAIRS = {"r1_indsl_time_split": "r1f_indsl_time_split", "r2_kythera_epoch_seconds": "r2f_kythera_epoch_seconds"}

def export_unscoped():
    out = []
    for c in PAIRS:
        app = open(f"benchmarks/{c}/app.py").read()
        fn = next(n for n in ast.parse(app.split(MARK)[0]).body if isinstance(n, ast.FunctionDef))
        orig = ast.get_source_segment(app, fn)
        for d in sorted(glob.glob(f"runs/*_{c}")):
            atts = sorted(glob.glob(d + "/attempt_*.json"), key=lambda p: int(p.rsplit("_", 1)[1].split(".")[0]))
            if not atts: continue
            recs = [json.load(open(a)) for a in atts]; last = recs[-1]
            diff = Path(d, "patch.diff").read_text() if Path(d, "patch.diff").exists() else ""
            dif = last.get("differential"); dif = dif.get("verdict") if isinstance(dif, dict) else dif
            out.append({"case": c, "run": os.path.basename(d), "attempts": len(recs), "success": last.get("success"),
                        "new_verdict": last.get("new_verdict"), "hidden_new": last.get("hidden_new"), "differential": dif,
                        "total_tokens_all_attempts": sum((r.get("usage") or {}).get("total_tokens", 0) for r in recs),
                        "upstream_function_unchanged": orig in (last.get("files") or {}).get("app.py", ""), "patch_diff": diff,
                        "scope": "unscoped (adapter was editable)"})
    Path("docs/real_cases/results_unscoped_20261029.json").write_text(json.dumps(out, indent=1) + "\n")
    for r in out: print(r["run"], r["attempts"], r["success"], r["differential"], r["total_tokens_all_attempts"], "function_unchanged=%s" % r["upstream_function_unchanged"])

def fix_app(text):
    text = text.split(MARK)[0]
    return text.replace(OLD_LINE, NEW_LINE).rstrip("\n") + "\n"

def scope(src, dst):
    s, d = Path("benchmarks") / src, Path("benchmarks") / dst
    if d.exists(): sys.exit(f"{d} exists")
    shutil.copytree(s, d, ignore=shutil.ignore_patterns("__pycache__"))
    full = (d / "app.py").read_text(); body, adapter = full.split(MARK)
    tree = ast.parse(body)
    imports = "\n".join(ast.get_source_segment(body, n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom)))
    fname = next(n.name for n in tree.body if isinstance(n, ast.FunctionDef))
    adapter_fn = re.search(r"def (\w+)\(", adapter).group(1)
    (d / "tests" / "adapter.py").write_text('"""Adapter (ours), read-only for the repair: JSON-friendly wrapper around the third-party function in app.py."""\n'
                                            f"{imports}\n\nfrom app import {fname}\n\n\n{adapter}")
    (d / "app.py").write_text(fix_app(full))
    for p in (d / "run_case.py", d / "tests" / "test_app.py"):
        t = p.read_text(); assert f"from app import {adapter_fn}" in t, p
        p.write_text(t.replace(f"from app import {adapter_fn}", f"from tests.adapter import {adapter_fn}"))
    for p in [d / "known_good.json", *sorted((d / "known_bad").glob("*.json"))]:
        j = json.loads(p.read_text()); j["files"]["app.py"] = fix_app(j["files"]["app.py"]); p.write_text(json.dumps(j, indent=1) + "\n")
    print("scoped:", d)

export_unscoped()
for a, b in PAIRS.items(): scope(a, b)
n = Path("docs/THIRD_PARTY_NOTICES.md"); t = n.read_text()
n.write_text(t.rstrip("\n") + "\n\nThe same upstream functions (same licenses as above) are also used in `benchmarks/r1f_indsl_time_split` and `benchmarks/r2f_kythera_epoch_seconds`.\n")
