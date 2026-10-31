"""Ask a model which functions of a folder might behave differently after an upgrade; the ones the patterns of `discover` do not cover.

    python -m patchpilot.suggest SRC_DIR [--endpoint http://127.0.0.1:8080/v1 | --model muse-spark-1.3] [--json out.json]
        [--manifest scan_draft.json --probes-dir probes] [--limit 40] [--include-pattern-hits]

`discover` finds a short list of known patterns, so many real breaks are not found (for example NumPy 2 printing numbers
differently). This command sends the source of each remaining function that PatchPilot can run (the same shape rules as `discover`,
in files that import pandas or NumPy) to a model and asks one question: may its result differ, or may it raise, when pandas goes from 2.x
to 3.0 or NumPy from 1.x to 2.x? The reply is parsed as JSON data and never executed. The answer is a hypothesis, not a finding: the
suggestions are listed as candidates (with the model's one-sentence reason), and only a run on both libraries with real inputs
(`propose` or `capture`, then `scan`) says whether the function really changes. The model is never asked to repair anything here.
The source of each function is sent to the model you choose (a hosted one, or a local one with --endpoint, which sends nothing off your
computer). --manifest writes a draft manifest for the suggestions only (placeholder inputs, as `discover` does). Existing files are
never overwritten. Standard library only.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from pathlib import Path

from patchpilot import discover, meta_client

MAX_SOURCE = 6000

SYSTEM = (
    "You review one Python function for behavior that changes when its libraries are upgraded from pandas 2.x to pandas 3.0 "
    "(copy-on-write, a new string dtype, datetime resolution, removed deprecated options) or from NumPy 1.x to NumPy 2.x "
    "(scalars print as np.float64(1.0) instead of 1.0, new type promotion rules for scalars, removed aliases). "
    "Reply with JSON only, no prose: {\"may_differ\": true or false, \"library\": \"pandas\" or \"numpy\", \"reason\": \"one sentence\"}. "
    "Say true only if the RESULT of the function could differ, or the function could raise, on the new version for ordinary inputs. "
    "Say false for code that behaves the same on both versions, and do not guess."
)


def imports_numpy(tree: ast.AST) -> bool:
    return any((isinstance(n, ast.Import) and any(a.name.split(".")[0] == "numpy" for a in n.names))
               or (isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == "numpy") for n in ast.walk(tree))


def runnable_functions(top: Path, include_pattern_hits: bool = False) -> list[dict]:
    """Top-level functions of the right shape in files that import pandas or NumPy (parse only)."""
    out = []
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames[:] = sorted(d for d in dirnames if d not in discover.SKIP_DIRS and not d.startswith("test_") and not d.endswith(".egg-info"))
        for fn in sorted(filenames):
            if not fn.endswith(".py") or fn.startswith("test_") or fn.endswith("_test.py") or fn == "conftest.py":
                continue
            path = Path(dirpath) / fn
            try:
                if path.stat().st_size > discover.MAX_BYTES:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
            except (OSError, SyntaxError, ValueError, RecursionError):
                continue
            pandas, numpy = discover.imports_pandas(tree), imports_numpy(tree)
            if not (pandas or numpy):
                continue
            names: dict[str, int] = {}
            for n in tree.body:
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    names[n.name] = names.get(n.name, 0) + 1
            for n in tree.body:
                if not isinstance(n, ast.FunctionDef) or names[n.name] > 1 or discover.signature_problem(n):
                    continue
                if not include_pattern_hits and sum(len(v) for v in discover.sites_in(n).values()):
                    continue
                code = ast.get_source_segment(text, n) or ""
                if not code or len(code) > MAX_SOURCE:
                    continue
                out.append({"file": path.relative_to(top).as_posix(), "function": n.name, "line": n.lineno,
                            "lib": "pandas" if pandas else "numpy", "params": discover.parameters(n), "code": code,
                            "root": os.path.relpath(discover.project_root(path, top), top).replace(os.sep, "/")})
    return out


def parse_answer(value) -> tuple[dict | None, str]:
    if not isinstance(value, dict) or not isinstance(value.get("may_differ"), bool):
        return None, "the reply must be a JSON object with a true/false field may_differ"
    lib = value.get("library")
    reason = value.get("reason")
    return {"may_differ": value["may_differ"], "library": lib if lib in ("pandas", "numpy") else None,
            "reason": reason.strip()[:300] if isinstance(reason, str) else ""}, ""


def ask_one(c: dict, model: str, endpoint: str | None, effort: str, chat=None) -> dict:
    from patchpilot import propose  # reuses the JSON extraction
    chat = chat or meta_client.chat
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"```python\n{c['code']}\n```"}]
    tokens, why = 0, ""
    for attempt in (1, 2):
        resp = chat(messages, model, reasoning_effort=effort, timeout_s=900 if endpoint else 240, endpoint=endpoint)
        tokens += (resp.get("usage") or {}).get("total_tokens") or 0
        reply = meta_client.text_of(resp)
        ans, why = parse_answer(propose.extract_json(reply))
        if ans is not None:
            return {**ans, "tokens": tokens}
        messages += [{"role": "assistant", "content": reply}, {"role": "user", "content": f"Not usable: {why}. Reply again with the JSON only."}]
    return {"may_differ": None, "library": None, "reason": f"no usable answer: {why}", "tokens": tokens}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src_dir")
    ap.add_argument("--model", help="model name (default: muse-glimmer with --endpoint, otherwise muse-spark-1.3)")
    ap.add_argument("--endpoint", help="base URL of a local OpenAI-compatible server (loopback only, no API key is sent)")
    ap.add_argument("--effort", default="low", choices=["minimal", "low", "medium", "high"])
    ap.add_argument("--limit", type=int, default=40, help="ask about at most N functions (default 40)")
    ap.add_argument("--include-pattern-hits", action="store_true", help="also ask about the functions `discover` already lists")
    ap.add_argument("--json", help="write the answers here")
    ap.add_argument("--manifest", help="write a draft scan manifest for the suggested functions (needs --probes-dir)")
    ap.add_argument("--probes-dir")
    a = ap.parse_args(argv)
    top = Path(a.src_dir)
    if not top.is_dir():
        print(f"suggest: {a.src_dir} is not a folder", file=sys.stderr)
        return 2
    if bool(a.manifest) != bool(a.probes_dir) or a.limit < 1:
        print("suggest: --manifest and --probes-dir go together, and --limit must be at least 1", file=sys.stderr)
        return 2
    for p in (a.json, a.manifest):
        if p and Path(p).exists():
            print(f"suggest: {p} exists; not overwriting", file=sys.stderr)
            return 2
    a.model = a.model or ("muse-glimmer" if a.endpoint else "muse-spark-1.3")
    funcs = runnable_functions(top, a.include_pattern_hits)
    total_found = len(funcs)
    funcs = funcs[:a.limit]
    print(f"{total_found} function(s) that PatchPilot can run and `discover` does not list; asking {a.model} about {len(funcs)}")
    answers, tokens, failed = [], 0, 0
    for k, c in enumerate(funcs):
        try:
            r = ask_one(c, a.model, a.endpoint, a.effort)
        except meta_client.MetaAuthError as e:
            print(f"suggest: {e}", file=sys.stderr)
            return 2
        except meta_client.MetaAPIError as e:
            r = {"may_differ": None, "library": None, "reason": f"model call failed: {e}", "tokens": 0}
        tokens += r["tokens"]
        failed += r["may_differ"] is None
        answers.append({**{k2: v for k2, v in c.items() if k2 != "code"}, **r})
        mark = {True: "MAY DIFFER", False: "no", None: "?"}[r["may_differ"]]
        print(f"  [{k + 1}/{len(funcs)}] {c['file']}:{c['function']}  {mark}  {r['reason']}")
    yes = [x for x in answers if x["may_differ"]]
    print(f"{len(yes)} suggested, {sum(x['may_differ'] is False for x in answers)} not, {failed} without an answer; {tokens} tokens")
    print("a suggestion is a hypothesis: give the function real inputs (`propose` or `capture`) and run `scan` to see whether it changes")
    if a.json:
        Path(a.json).write_text(json.dumps({"model": a.model, "asked": len(funcs), "tokens": tokens, "answers": answers}, indent=1) + "\n")
        print(f"wrote {a.json}")
    if a.manifest:
        res = {"candidates": [{**x, "lib": x["library"] or x["lib"]} for x in yes]}
        n, refused = discover.write_manifest(res, top, Path(a.manifest), Path(a.probes_dir))
        if refused:
            print("suggest: not overwritten: " + ", ".join(refused), file=sys.stderr)
            return 2
        print(f"wrote {a.manifest} with {n} target(s) and placeholder inputs in {a.probes_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
