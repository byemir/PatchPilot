"""Classify the sites found by scripts/census.py by the code that contains them.

    python scripts/census_scope.py REPOS_DIR CENSUS_JSON [--json out.json]

REPOS_DIR holds one folder per repository (the names used as keys in CENSUS_JSON, written by `census.py --json`). Each site
`kind file:line` is placed in one class: `function` (a module-level function with at least one parameter and no `self`/`cls`: the
shape PatchPilot can check), `method` (inside a class, or a function nested in another function), `no_args` (a module-level function without parameters), `module` (code at module
level), `notebook`. For a `function` the output also names the function and its first parameter names, never any source text.
The code is only parsed with `ast`; nothing is imported or run. Standard library only.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
import warnings
from pathlib import Path

warnings.simplefilter("ignore")
SELF_NAMES = {"self", "cls", "mcs", "warp_self"}


def classify(source: str, line: int) -> tuple[str, str]:
    """Return (class, detail) for the site at `line` of `source`."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return "unparsed", ""
    chain: list[ast.AST] = []

    def walk(node: ast.AST) -> None:
        for c in ast.iter_child_nodes(node):
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and c.lineno <= line <= (c.end_lineno or c.lineno):
                chain.append(c)
                walk(c)
                return
            walk(c)

    walk(tree)
    if not chain:
        return "module", ""
    first = chain[0]
    if isinstance(first, ast.ClassDef) or len(chain) > 1:
        return "method", ""
    args = [a.arg for a in first.args.args + first.args.posonlyargs]
    if not args:
        return "no_args", first.name
    if args[0] in SELF_NAMES:
        return "method", ""
    return "function", f"{first.name}({', '.join(args[:4])}{', ...' if len(args) > 4 else ''})"


def scope_repo(root: Path, sites: list[str]) -> list[dict]:
    out = []
    for s in sites:
        kind, loc = s.split(" ", 1)
        f, ln = loc.rsplit(":", 1)
        if f.endswith(".ipynb"):
            out.append({"kind": kind, "site": loc, "class": "notebook", "detail": ""})
            continue
        try:
            cls, detail = classify((root / f).read_text(encoding="utf-8", errors="replace"), int(ln))
        except OSError:
            cls, detail = "missing", ""
        out.append({"kind": kind, "site": loc, "class": cls, "detail": detail})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("repos_dir")
    ap.add_argument("census_json")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    census = json.loads(Path(a.census_json).read_text())
    result = {}
    totals: dict[str, int] = {}
    for name in sorted(census):
        rows = scope_repo(Path(a.repos_dir) / name, census[name]["sites"])
        result[name] = rows
        for r in rows:
            totals[r["class"]] = totals.get(r["class"], 0) + 1
    for name, rows in result.items():
        fn = [r for r in rows if r["class"] == "function"]
        print(f"{name:40} sites {len(rows):4}   module-level functions {len(fn)}")
        for r in fn[:20]:
            print(f"    {r['kind']:9} {r['site']}  {r['detail']}")
    print("totals:", totals)
    if a.json:
        Path(a.json).write_text(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
