"""Find the functions in a folder that PatchPilot can check, and draft the scan files for them.

    python -m patchpilot.discover SRC_DIR [--json discover.json] [--manifest scan_draft.json --probes-dir probes] [--limit 50]

The code is only parsed with `ast`: nothing is imported or run. A function is listed when it contains at least one of three
places that the pandas 3.0 migration guide warns about (chained assignment, an in-place method on a selected column, a datetime
turned into an integer (also an index read through `np.array(x.index, dtype=int64)`, `.asi8` or `x.index[i].value`), a check `x.dtype == object` on a column that may hold text) AND has the shape PatchPilot can run: a top-level function, at least one parameter, no `self`/`cls`,
only plain named parameters (no `*args`, `**kwargs`, positional-only), not async, and a name used once in its file. Sites
that sit anywhere else (methods, module-level code, notebooks, functions without parameters, other signatures) are counted by
reason and not listed. A listed function is a candidate, not a confirmed break: that needs inputs and a run (the scan command).
The patterns are a short list, so many real breaks are not found (for example NumPy 2 changes in how numbers print): a function that
is not listed has not been shown to be safe.

--json writes the candidates with their parameter names, annotations and literal defaults (what a later step needs to propose
inputs). --manifest writes a scan manifest with one target per candidate and, in --probes-dir, one placeholder input file per
candidate (parameter name -> its literal default, or null), and each target is marked `"placeholder": true`. The placeholders are
NOT real inputs: fill them (with `python -m patchpilot.capture`, which records them from your own tests, or let a model propose
inputs with `python -m patchpilot.propose`) before running `scan`. Existing files are never
overwritten. Standard library only.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
import warnings
from pathlib import Path

warnings.simplefilter("ignore")  # old source files raise SyntaxWarning on parse

SKIP_DIRS = {".git", ".hg", ".venv", "venv", "env", ".tox", ".sandboxes", "node_modules", "__pycache__", "site-packages",
             "build", "dist", ".eggs", "tests", "test", "testing", "benchmarks", "asv_bench", "docs"}
SELF_NAMES = {"self", "cls", "mcs"}
INT_NAMES = {"int64", "i8", "int", "int32", "np.int64", "numpy.int64"}
MAX_BYTES = 2_000_000


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


def _is_object_check(n: ast.Compare) -> bool:
    """x.dtype == object / "object" / "O" (and !=, is): on pandas 3 text columns no longer have the object dtype."""
    sides = [n.left] + list(n.comparators)
    has_dtype = any(isinstance(x, ast.Attribute) and x.attr == "dtype" for x in sides)
    has_obj = any((isinstance(x, ast.Name) and x.id == "object") or (isinstance(x, ast.Constant) and x.value in ("object", "O")) for x in sides)
    return has_dtype and has_obj and all(isinstance(o, (ast.Eq, ast.NotEq, ast.Is, ast.IsNot)) for o in n.ops)


def _index_to_int(n: ast.AST) -> bool:
    """np.array(x.index, dtype=np.int64) / np.asarray(...), x.index.asi8, x.index[i].value: a datetime index read as integers."""
    if isinstance(n, ast.Call) and _name(n.func).split(".")[-1] in ("array", "asarray") and n.args:
        dt = next((k.value for k in n.keywords if k.arg == "dtype"), None)
        a0 = n.args[0]
        return dt is not None and _name(dt) in INT_NAMES and isinstance(a0, ast.Attribute) and a0.attr == "index"
    if isinstance(n, ast.Attribute) and n.attr == "asi8":
        return True
    if isinstance(n, ast.Attribute) and n.attr == "value" and isinstance(n.value, ast.Subscript):
        v = n.value.value
        return isinstance(v, ast.Attribute) and v.attr == "index"
    return False


def sites_in(node: ast.AST) -> dict[str, list[int]]:
    """Line numbers of the patterns inside `node`."""
    hits = {"chained": [], "inplace": [], "datetime": [], "objdtype": []}
    dt_names = set()  # names assigned from a datetime expression, so that `ts = pd.to_datetime(x)` ... `ts.astype("int64")` counts
    for n in ast.walk(node):
        if isinstance(n, ast.Assign) and _has_datetime(n.value):
            dt_names.update(t.id for t in n.targets if isinstance(t, ast.Name))
    for n in ast.walk(node):
        if isinstance(n, ast.Compare) and _is_object_check(n):
            hits["objdtype"].append(n.lineno)
        if _index_to_int(n):
            hits["datetime"].append(n.lineno)
        if isinstance(n, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            if any(_chained(t) for t in targets):
                hits["chained"].append(n.lineno)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if any(k.arg == "inplace" and isinstance(k.value, ast.Constant) and k.value.value is True for k in n.keywords) \
                    and isinstance(n.func.value, ast.Subscript):
                hits["inplace"].append(n.lineno)
            if n.func.attr in ("astype", "view") and n.args and _name(n.args[0]) in INT_NAMES \
                    and (_has_datetime(n.func.value) or (isinstance(n.func.value, ast.Name) and n.func.value.id in dt_names)):
                hits["datetime"].append(n.lineno)
    return hits


def imports_pandas(tree: ast.AST) -> bool:
    return any((isinstance(n, ast.Import) and any(a.name.split(".")[0] == "pandas" for a in n.names))
               or (isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == "pandas") for n in ast.walk(tree))


def notebook_source(text: str) -> str | None:
    """The code cells of a notebook as one source text (IPython magic lines dropped); None if it is not a notebook."""
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


def signature_problem(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """'' when PatchPilot can call the function with named arguments, otherwise the reason it cannot."""
    if isinstance(fn, ast.AsyncFunctionDef):
        return "async"
    a = fn.args
    plain = a.posonlyargs + a.args + a.kwonlyargs
    if not plain and not a.vararg and not a.kwarg:
        return "no_args"
    if a.posonlyargs or a.vararg or a.kwarg:
        return "signature"
    if a.args and a.args[0].arg in SELF_NAMES:
        return "method"
    return ""


def parameters(fn: ast.FunctionDef) -> list[dict]:
    a = fn.args
    pos = a.args
    defaults = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
    rows = []
    for arg, d in list(zip(pos, defaults)) + list(zip(a.kwonlyargs, a.kw_defaults)):
        row = {"name": arg.arg, "annotation": ast.unparse(arg.annotation) if arg.annotation is not None else None, "default": None, "has_default": d is not None}
        if d is not None:
            try:
                value = ast.literal_eval(d)
                json.dumps(value, allow_nan=False)
                row["default"] = value
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                row["has_default"] = True  # a default that is not a plain value
                row["default"] = None
        rows.append(row)
    return rows


def project_root(path: Path, top: Path) -> Path:
    """The folder from which the file can be imported as a module: climb while the parent folder is a package."""
    p = path.parent
    while (p / "__init__.py").exists() and p != top.parent and p != p.parent:
        p = p.parent
    return p


def analyse_file(path: Path, top: Path) -> tuple[list[dict], dict[str, int]]:
    """(candidates, skipped-by-reason counts) for one file."""
    skipped: dict[str, int] = {}

    def skip(reason: str, n: int = 1) -> None:
        skipped[reason] = skipped.get(reason, 0) + n

    try:
        if path.stat().st_size > MAX_BYTES:
            return [], skipped
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], skipped
    if path.suffix == ".ipynb":
        src = notebook_source(text)
        if src is None:
            return [], skipped
        try:
            tree = ast.parse(src)
        except (SyntaxError, ValueError, RecursionError):
            return [], skipped
        if imports_pandas(tree):
            skip("notebook", sum(len(v) for v in sites_in(tree).values()))
        return [], {k: v for k, v in skipped.items() if v}
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return [], skipped
    if not imports_pandas(tree):
        return [], skipped
    names: dict[str, int] = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names[n.name] = names.get(n.name, 0) + 1
    cands = []
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            hits = sites_in(n)
            total = sum(len(v) for v in hits.values())
            if not total:
                continue
            problem = signature_problem(n)
            if not problem and names[n.name] > 1:
                problem = "duplicate_name"
            if problem:
                skip(problem, total)
                continue
            rel = path.relative_to(top)
            root = project_root(path, top)
            cands.append({
                "file": rel.as_posix(), "function": n.name, "line": n.lineno,
                "chained": len(hits["chained"]), "inplace": len(hits["inplace"]), "datetime": len(hits["datetime"]), "objdtype": len(hits["objdtype"]),
                "params": parameters(n), "decorated": bool(n.decorator_list),
                "root": os.path.relpath(root, top).replace(os.sep, "/"),
            })
        elif isinstance(n, ast.ClassDef):
            total = sum(len(v) for v in sites_in(n).values())
            if total:
                skip("method", total)
        else:
            total = sum(len(v) for v in sites_in(n).values())
            if total:
                skip("module", total)
    return cands, skipped


def discover(top: Path, limit: int | None = None) -> dict:
    """Walk `top` and return {"candidates": [...], "skipped": {reason: sites}, "files": n}."""
    cands: list[dict] = []
    skipped: dict[str, int] = {}
    files = 0
    for dirpath, dirnames, filenames in os.walk(top):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("test_") and not d.endswith(".egg-info"))
        for fn in sorted(filenames):
            if not fn.endswith((".py", ".ipynb")) or fn.startswith("test_") or fn.endswith("_test.py") or fn == "conftest.py":
                continue
            files += 1
            c, s = analyse_file(Path(dirpath) / fn, top)
            cands += c
            for k, v in s.items():
                skipped[k] = skipped.get(k, 0) + v
    cands.sort(key=lambda c: (-(c["chained"] + c["inplace"] + c["datetime"]), c["file"], c["function"]))
    total = len(cands)
    if limit is not None:
        cands = cands[:limit]
    return {"files": files, "total_candidates": total, "candidates": cands, "skipped": dict(sorted(skipped.items()))}


def probe_name(c: dict) -> str:
    stem = c["file"].rsplit(".", 1)[0].replace("/", "_")
    return f"{stem}.{c['function']}.json"


def placeholder(c: dict) -> list[dict]:
    """One probe whose values are the literal defaults (or null). It is a form to fill, not a real input."""
    return [{p["name"]: p["default"] for p in c["params"]}]


def write_manifest(result: dict, top: Path, manifest: Path, probes_dir: Path) -> tuple[int, list[str]]:
    """Write the draft manifest and the placeholder inputs; return (targets written, refused paths). Nothing is overwritten."""
    if manifest.exists():
        return 0, [str(manifest)]
    base = manifest.resolve().parent
    planned = [(c, probes_dir / probe_name(c)) for c in result["candidates"]]
    refused = [str(pf) for _, pf in planned if pf.exists()]
    if refused:
        return 0, refused  # nothing is written when any placeholder file already exists
    probes_dir.mkdir(parents=True, exist_ok=True)
    targets = []
    for c, pf in planned:
        pf.write_text(json.dumps(placeholder(c), indent=1) + "\n")
        targets.append({"file": os.path.relpath((top / c["file"]).resolve(), base).replace(os.sep, "/"), "function": c["function"], "lib": "pandas",
                        "inputs": os.path.relpath(pf.resolve(), base).replace(os.sep, "/"), "placeholder": True,
                        "root": os.path.relpath((top / c["root"]).resolve(), base).replace(os.sep, "/")})
    note = ("DRAFT written by `patchpilot.discover`. The input files are placeholders (defaults or null), not real inputs: fill them, "
            "for example with `python -m patchpilot.capture`, before running `scan`. Add \"old\" and \"new\" interpreters to a target "
            "if the project needs its own dependencies.")
    manifest.write_text(json.dumps({"note": note, "targets": targets}, indent=1) + "\n")
    return len(targets), refused


REASONS = {
    "method": "inside a class or a function that takes self/cls",
    "module": "in module-level code",
    "notebook": "in a notebook",
    "no_args": "in a function without parameters",
    "signature": "in a function with *args, **kwargs or positional-only parameters",
    "async": "in an async function",
    "duplicate_name": "in a function whose name is used more than once in its file",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src_dir")
    ap.add_argument("--json", help="write the candidates and the skipped counts here")
    ap.add_argument("--manifest", help="write a draft scan manifest here (needs --probes-dir)")
    ap.add_argument("--probes-dir", help="folder for the placeholder input files")
    ap.add_argument("--limit", type=int, help="keep only the first N candidates (most sites first)")
    a = ap.parse_args(argv)
    top = Path(a.src_dir)
    if not top.is_dir():
        print(f"discover: {a.src_dir} is not a folder", file=sys.stderr)
        return 2
    if bool(a.manifest) != bool(a.probes_dir):
        print("discover: --manifest and --probes-dir go together", file=sys.stderr)
        return 2
    if a.limit is not None and a.limit < 1:
        print("discover: --limit must be at least 1", file=sys.stderr)
        return 2
    res = discover(top, a.limit)
    cands = res["candidates"]
    print(f"{res['files']} files read; {res['total_candidates']} candidate function(s) that PatchPilot can run, {len(cands)} shown")
    for c in cands:
        kinds = ", ".join(f"{k} {c[k]}" for k in ("chained", "inplace", "datetime", "objdtype") if c[k])
        args = ", ".join(p["name"] for p in c["params"][:5]) + (", ..." if len(c["params"]) > 5 else "")
        print(f"  {c['file']}:{c['line']}  {c['function']}({args})  [{kinds}]")
    if res["skipped"]:
        print("sites PatchPilot cannot check, by place:")
        for k, v in res["skipped"].items():
            print(f"  {v:4d}  {REASONS.get(k, k)}")
    print("candidates are places that may behave differently on pandas 3, not confirmed breaks; run `scan` with real inputs to find out")
    if a.json:
        jp = Path(a.json)
        if jp.exists():
            print(f"discover: {jp} exists; not overwriting", file=sys.stderr)
            return 2
        jp.write_text(json.dumps(res, indent=1) + "\n")
        print(f"wrote {jp}")
    if a.manifest:
        n, refused = write_manifest(res, top, Path(a.manifest), Path(a.probes_dir))
        if refused:
            print("discover: not overwritten: " + ", ".join(refused), file=sys.stderr)
            return 2
        print(f"wrote {a.manifest} with {n} target(s) and placeholder inputs in {a.probes_dir}: fill the inputs before `scan`")
    return 0


if __name__ == "__main__":
    sys.exit(main())
