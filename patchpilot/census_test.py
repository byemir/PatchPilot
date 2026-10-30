"""Offline check of scripts/census.py on made-up source. Run: python -m patchpilot.census_test"""
from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("census", Path(__file__).resolve().parent.parent / "scripts" / "census.py")
census = importlib.util.module_from_spec(spec)
spec.loader.exec_module(census)
passed = 0


def check(name, cond, detail=""):
    global passed
    assert cond, f"{name}: {detail}"
    passed += 1
    print(f"ok  {name}")


def hits(body, imp="import pandas as pd\n"):
    r = census.scan_source(imp + body)
    return None if r is None else {k: len(v) for k, v in r["hits"].items()}


check("chained assignment with a column then a mask is found", hits('df["big"][df["a"] > 5] = True\n')["chained"] == 1)
check("a mask then a column is found", hits('df[df.a > 5]["b"] = 2\n')["chained"] == 1)
check("loc then a column is found", hits('df.loc[rows]["b"] = 2\n')["chained"] == 1)
check("a nested dict is not chained assignment", hits('d["a"]["b"] = 1\n')["chained"] == 0)
check("an indexed list in a dict is not chained assignment", hits('d["a"][i] = 1\n')["chained"] == 0)
check("in-place on a column is found", hits('df["c"].fillna(0, inplace=True)\n')["inplace"] == 1)
check("in-place on the whole frame is not", hits('df.fillna(0, inplace=True)\n')["inplace"] == 0)
check("a datetime turned into int64 is found", hits('x = pd.to_datetime(s).astype("int64") // 10**9\ny = df["t"].dt.floor("s").view("i8")\n')["datetime"] == 2)
check("an ordinary column to int64 is not", hits('df["n"].astype("int64")\n')["datetime"] == 0)
check("a file without pandas is not counted", hits('df["big"][df["a"] > 5] = True\n', imp="import numpy as np\n") is None)
check("a file that does not parse is skipped", census.scan_source("def (:\n") is None)
NB = ('{"cells": [{"cell_type": "code", "source": ["%matplotlib inline\\n", "import pandas as pd\\n", "df[\'c\'].fillna(0, inplace=True)"]},'
      ' {"cell_type": "markdown", "source": ["df[\'c\'].fillna(0, inplace=True)"]}]}')
nb_result = census.scan_source(census.notebook_source(NB))
check("a notebook is read from its code cells only", nb_result is not None and len(nb_result["hits"]["inplace"]) == 1)
with tempfile.TemporaryDirectory() as t:
    p = Path(t) / "pkg"
    (p / "tests").mkdir(parents=True)
    (p / "a.py").write_text("import pandas as pd\ndf['c'].fillna(0, inplace=True)\n")
    (p / "tests" / "test_a.py").write_text("import pandas as pd\ndf['c'].fillna(0, inplace=True)\n")
    r = census.scan_package(p)
    check("test folders are left out and the result has no source text", r["inplace"] == 1 and r["files"] == 1 and r["sites"] == ["inplace a.py:2"], str(r))
print(f"census_test: {passed} checks passed")
