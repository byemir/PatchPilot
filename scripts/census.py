"""Count places in Python source that match three patterns the pandas 3.0 migration guide warns about.

    python scripts/census.py PACKAGE_DIR [PACKAGE_DIR ...] [--json out.json]

The code is only parsed with `ast`; it is never imported or run. Only files that import pandas are counted. Output is counts and
file:line positions, no source text. For notebooks the line number is the line in the joined code cells. A hit is a *site that may behave differently on pandas 3*, not a confirmed break: that needs
inputs and a run (what the scan command does). Standard library only.

  chained    chained assignment: df["c"][mask] = v, df[mask]["c"] = v, df.loc[rows]["c"] = v
  inplace    an in-place method on a selected column: df["c"].fillna(0, inplace=True)
  datetime   a datetime turned into an integer: pd.to_datetime(s).astype("int64"), s.dt....astype("int64"), .view("i8")
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
import warnings
from pathlib import Path

warnings.simplefilter("ignore")  # old source files raise SyntaxWarning on parse

INT_NAMES = {"int64", "i8", "int", "int32", "np.int64", "numpy.int64"}


def _name(n: ast.AST) -> str:
    if isinstance(n, ast.Constant) and isinstance(n.value, str):
        return n.value
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        base = _name(n.value)
        return f"{base}.{n.attr}" if base else n.attr
    return ""


def _is_mask(n: ast.AST) -> bool:
    return isinstance(n, (ast.Compare, ast.BoolOp)) or (isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.Invert, ast.Not)))


def _is_str(n: ast.AST) -> bool:
    return isinstance(n, ast.Constant) and isinstance(n.value, str)


def _chained(t: ast.AST) -> bool:
    if not isinstance(t, ast.Subscript) or not isinstance(t.value, ast.Subscript):
        return False
    inner = t.value
    if isinstance(inner.value, ast.Attribute) and inner.value.attr in ("loc", "iloc"):  # df.loc[rows]["c"] = v
        return True
    if _is_str(inner.slice) and _is_mask(t.slice):  # df["c"][mask] = v
        return True
    if _is_mask(inner.slice) and _is_str(t.slice):  # df[mask]["c"] = v
        return True
    return False


def _has_datetime(n: ast.AST) -> bool:
    for x in ast.walk(n):
        if isinstance(x, ast.Attribute) and x.attr == "dt":
            return True
        if isinstance(x, ast.Call) and _name(x.func).split(".")[-1] in ("to_datetime", "Timestamp", "DatetimeIndex", "date_range"):
            return True
    return False


def scan_source(src: str) -> dict | None:
    """Return the hits of one file, or None when it does not import pandas or does not parse."""
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError, RecursionError):
        return None
    if not any((isinstance(n, ast.Import) and any(a.name.split(".")[0] == "pandas" for a in n.names))
               or (isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == "pandas") for n in ast.walk(tree)):
        return None
    hits = {"chained": [], "inplace": [], "datetime": []}
    for n in ast.walk(tree):
        if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            if any(_chained(t) for t in targets):
                hits["chained"].append(n.lineno)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if any(k.arg == "inplace" and isinstance(k.value, ast.Constant) and k.value.value is True for k in n.keywords) \
                    and isinstance(n.func.value, ast.Subscript):
                hits["inplace"].append(n.lineno)
            if n.func.attr in ("astype", "view") and n.args and _name(n.args[0]) in INT_NAMES and _has_datetime(n.func.value):
                hits["datetime"].append(n.lineno)
    loc = sum(1 for line in src.splitlines() if line.strip() and not line.strip().startswith("#"))
    return {"hits": hits, "loc": loc}


def notebook_source(text: str) -> str | None:
    """The code cells of a notebook as one source text (IPython magic lines are dropped); None if it is not a notebook."""
    try:
        nb = json.loads(text)
        cells = nb["cells"] if "cells" in nb else [c for ws in nb["worksheets"] for c in ws["cells"]]
    except (ValueError, KeyError, TypeError):
        return None
    out = []
    for c in cells:
        if isinstance(c, dict) and c.get("cell_type") == "code":
            src = c.get("source", c.get("input", ""))
            src = "".join(src) if isinstance(src, list) else str(src)
            out.append("\n".join("" if ln.lstrip().startswith(("%", "!", "?")) else ln for ln in src.splitlines()))
    return "\n".join(out)


def scan_package(root: Path) -> dict:
    out = {"files": 0, "pandas_files": 0, "loc": 0, "chained": 0, "inplace": 0, "datetime": 0, "sites": []}
    for f in sorted(list(root.rglob("*.py")) + list(root.rglob("*.ipynb"))):
        rel = f.relative_to(root)
        if any(p in ("tests", "test", "testing", "benchmarks", "asv_bench") or p.startswith("test_") for p in rel.parts):
            continue
        out["files"] += 1
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            if f.suffix == ".ipynb":
                text = notebook_source(text)
            r = scan_source(text) if text is not None else None
        except OSError:
            continue
        if r is None:
            continue
        out["pandas_files"] += 1
        out["loc"] += r["loc"]
        for kind, lines in r["hits"].items():
            out[kind] += len(lines)
            out["sites"] += [f"{kind} {rel}:{ln}" for ln in lines]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    res = {}
    for d in a.dirs:
        p = Path(d)
        if not p.is_dir():
            print(f"census: {d} is not a folder", file=sys.stderr)
            return 2
        res[p.name] = scan_package(p)
    for name, r in res.items():
        print(f"{name:24s} pandas files {r['pandas_files']:4d}/{r['files']:<4d} loc {r['loc']:7d}  chained {r['chained']:3d}  inplace {r['inplace']:3d}  datetime {r['datetime']:3d}")
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
