"""Offline checks for `patchpilot.discover` (no model, no key; nothing is run, the code is only parsed)."""
import contextlib
import io
import json
import tempfile
from pathlib import Path

from patchpilot import discover

passed = 0
REPO = Path(__file__).resolve().parent.parent


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed
    assert cond, f"{name}: {detail}"
    passed += 1
    print(f"ok  {name}")


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = discover.main(argv)
    return rc, buf.getvalue()


SRC = '''import pandas as pd
import numpy as np


def chained(df, limit=5):
    df["a"][df["a"] > limit] = 0
    return df


def fill(df):
    df["a"].fillna(0, inplace=True)
    return df


def epoch(stamps):
    ts = pd.to_datetime(pd.Series(stamps))
    return ts.astype("int64")


def direct(s):
    return pd.to_datetime(s).astype("int64")


def kinds(s, flag=True, tags=None, other=object()):
    if s.dtype == object:
        return 1
    return 0


def clean(df):
    return df.assign(b=1)


def index_seconds(data):
    x = (np.array(data.index, dtype=np.int64) - data.index[0].value) / 1e9
    return x


def asi(data):
    return data.index.asi8


class Box:
    def method(self, df):
        df["a"].fillna(0, inplace=True)

    @staticmethod
    def static(df):
        df["a"].fillna(0, inplace=True)


def noargs():
    pd.DataFrame()["a"].fillna(0, inplace=True)


def wild(*args, **kw):
    args[0]["a"].fillna(0, inplace=True)


async def later(df):
    df["a"].fillna(0, inplace=True)


def twice(df):
    df["a"].fillna(0, inplace=True)


def twice(df, other):
    df["a"].fillna(1, inplace=True)


def selfish(self, df):
    df["a"].fillna(0, inplace=True)


def positional(df, /, x):
    df["a"].fillna(0, inplace=True)


def outer(df):
    def inner(d):
        d["a"].fillna(0, inplace=True)
    inner(df)
    return df


df_module = pd.DataFrame({"a": [1]})
df_module["a"].fillna(0, inplace=True)
'''

with tempfile.TemporaryDirectory() as t:
    tmp = Path(t)
    proj = tmp / "proj"
    (proj / "pkg" / "sub").mkdir(parents=True)
    (proj / "pkg" / "__init__.py").write_text("")
    (proj / "pkg" / "sub" / "__init__.py").write_text("")
    (proj / "pkg" / "sub" / "mod.py").write_text(SRC)
    (proj / "flat.py").write_text("import pandas as pd\n\n\ndef f(x):\n    x['c'].fillna(0, inplace=True)\n    return x\n")
    (proj / "nopandas.py").write_text("def f(x):\n    x['c'].fillna(0, inplace=True)\n")
    (proj / "broken.py").write_text("import pandas as pd\ndef (:\n")
    (proj / "tests").mkdir()
    (proj / "tests" / "t.py").write_text("import pandas as pd\n\n\ndef g(x):\n    x['c'].fillna(0, inplace=True)\n")
    (proj / "test_top.py").write_text("import pandas as pd\n\n\ndef g(x):\n    x['c'].fillna(0, inplace=True)\n")
    (proj / ".venv").mkdir()
    (proj / ".venv" / "v.py").write_text("import pandas as pd\n\n\ndef g(x):\n    x['c'].fillna(0, inplace=True)\n")
    nb = {"cells": [{"cell_type": "code", "source": ["import pandas as pd\n", "%matplotlib inline\n", "df = pd.DataFrame()\n", "df['a'].fillna(0, inplace=True)\n"]}]}
    (proj / "note.ipynb").write_text(json.dumps(nb))

    res = discover.discover(proj)
    names = {(c["file"], c["function"]): c for c in res["candidates"]}
    m = "pkg/sub/mod.py"
    check("a chained assignment in a top-level function is a candidate", (m, "chained") in names and names[(m, "chained")]["chained"] == 1)
    check("an in-place method on a column is a candidate", (m, "fill") in names and names[(m, "fill")]["inplace"] == 1)
    check("a datetime turned into an integer through a variable is a candidate", (m, "epoch") in names and names[(m, "epoch")]["datetime"] == 1)
    check("the direct form of the same conversion is a candidate", (m, "direct") in names and names[(m, "direct")]["datetime"] == 1)
    check("a check of the object dtype is a candidate", (m, "kinds") in names and names[(m, "kinds")]["objdtype"] == 1)
    check("a datetime index read as integers (np.array, .value, .asi8) is a candidate",
          (m, "index_seconds") in names and names[(m, "index_seconds")]["datetime"] == 2 and (m, "asi") in names and names[(m, "asi")]["datetime"] == 1,
          str({k: v["datetime"] for k, v in names.items()}))
    check("a function without a pattern is not listed", (m, "clean") not in names)
    check("methods, functions without parameters, *args, async, duplicate names, self and positional-only are not listed",
          not any(f in {"method", "static", "noargs", "wild", "later", "twice", "selfish", "positional"} for _, f in names), str(sorted(names)))
    check("a function that holds a nested function is listed once, as the outer function", (m, "outer") in names and ("pkg/sub/mod.py", "inner") not in names)
    check("the skipped sites are counted by reason",
          res["skipped"].get("method") == 3 and res["skipped"].get("no_args") == 1 and res["skipped"].get("signature") == 2
          and res["skipped"].get("async") == 1 and res["skipped"].get("duplicate_name") == 2 and res["skipped"].get("module") == 1
          and res["skipped"].get("notebook") == 1, str(res["skipped"]))
    check("files that do not import pandas, do not parse, or sit in tests, test files or a virtualenv are ignored",
          all(c["file"] in (m, "flat.py") for c in res["candidates"]) and "broken.py" not in json.dumps(res) and ".venv" not in json.dumps(res))
    check("the package root is found by climbing through the __init__ files", names[(m, "fill")]["root"] == "." and names[("flat.py", "f")]["root"] == ".")
    sub = discover.discover(proj / "pkg")
    check("a scan of the package folder itself puts the root one level up", {c["root"] for c in sub["candidates"]} == {".."}, str({c["root"] for c in sub["candidates"]}))
    params = {p["name"]: p for p in names[(m, "kinds")]["params"]}
    check("parameters keep their names, annotations and plain defaults",
          list(params) == ["s", "flag", "tags", "other"] and params["flag"]["default"] is True and params["flag"]["has_default"]
          and params["tags"]["default"] is None and params["other"]["has_default"] and params["other"]["default"] is None and not params["s"]["has_default"])
    check("candidates are ordered by number of sites, then by file and name", [c["function"] for c in res["candidates"]][:1] != [] and res["total_candidates"] == len(res["candidates"]))
    check("--limit keeps the first candidates only", len(discover.discover(proj, 2)["candidates"]) == 2 and discover.discover(proj, 2)["total_candidates"] == res["total_candidates"])

    # command line, json, manifest and placeholders
    out = tmp / "out"
    out.mkdir()
    rc, text = run([str(proj), "--json", str(out / "d.json"), "--manifest", str(out / "scan.json"), "--probes-dir", str(out / "probes")])
    check("the command succeeds and says that candidates are not confirmed breaks", rc == 0 and "not confirmed breaks" in text and "fill the inputs" in text, text)
    man = json.loads((out / "scan.json").read_text())
    check("the manifest has one target per candidate with the keys scan needs",
          len(man["targets"]) == res["total_candidates"] and all({"file", "function", "lib", "inputs", "root"} <= set(x) for x in man["targets"])
          and "placeholder" in man["note"])
    ok_paths = all((out / x["file"]).resolve().is_file() and (out / x["inputs"]).resolve().is_file() and (out / x["root"]).resolve().is_dir() for x in man["targets"])
    check("every path in the manifest exists, relative to the manifest", ok_paths)
    check("every target is marked as a placeholder", all(x.get("placeholder") is True for x in man["targets"]))
    t_kinds = next(x for x in man["targets"] if x["function"] == "kinds")
    probe = json.loads((out / t_kinds["inputs"]).read_text())
    check("the placeholder input holds the defaults, null where there is none", probe == [{"s": None, "flag": True, "tags": None, "other": None}], str(probe))
    check("the json file holds the candidates and the skipped counts", {"candidates", "skipped", "files"} <= set(json.loads((out / "d.json").read_text())))

    rc, text = run([str(proj), "--json", str(out / "d.json")])
    check("an existing json file is not overwritten", rc == 2 and "not overwriting" in text, text)
    rc, text = run([str(proj), "--manifest", str(out / "scan.json"), "--probes-dir", str(out / "probes")])
    check("an existing manifest is not overwritten", rc == 2 and "not overwritten" in text, text)
    before = (out / "scan.json").read_text()
    out2 = tmp / "out2"
    (out2 / "probes").mkdir(parents=True)
    (out2 / "probes" / discover.probe_name(res["candidates"][0])).write_text("keep")
    rc, text = run([str(proj), "--manifest", str(out2 / "scan.json"), "--probes-dir", str(out2 / "probes")])
    check("an existing placeholder stops the run before anything is written",
          rc == 2 and not (out2 / "scan.json").exists() and len(list((out2 / "probes").iterdir())) == 1, text)
    check("the first manifest was not touched", (out / "scan.json").read_text() == before)
    check("--manifest without --probes-dir is refused", run([str(proj), "--manifest", str(tmp / "x.json")])[0] == 2)
    check("a missing folder is refused", run([str(tmp / "nope")])[0] == 2)
    check("--limit below 1 is refused", run([str(proj), "--limit", "0"])[0] == 2)

# the example code bases written for this project: known silent breaks (see docs/APP_RUNS.md)
shop = discover.discover(REPO / "examples" / "shop")
got = {c["function"] for c in shop["candidates"]}
check("on the shop example the candidates are four of its seven silent functions and none of its healthy ones",
      got == {"fill_missing_region", "flag_big_orders", "last_seen_epoch", "clean_names"}, str(got))
check("nothing is run: the module imports no scan or sandbox code", "sandbox" not in discover.__dict__ and "subprocess" not in discover.__dict__)
print(f"discover_test: {passed} checks passed")
