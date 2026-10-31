# How common are the patterns this tool targets? A static count

Question: how often do three pandas-3 patterns appear in public Python code? The counts below are an upper bound on *potential* sites, not on confirmed breaks. The list of packages and repositories was written down before any count was run (`docs/census/PREREGISTERED.txt`, 2026-10-30 21:10 Istanbul). Every item on it is reported, including zeros.

## Method (`scripts/census.py`, standard library only)

- Parses each `.py` file (and the code cells of each `.ipynb`) with `ast`; only files that import pandas are counted; folders named `tests`, `test`, `testing`, `benchmarks`, `asv_bench` are skipped.
- Three patterns, each a *potential* silent change in pandas 3 (the first two are Copy-on-Write: the write no longer reaches the original; the third is the datetime resolution change):
  - `chained`: assignment through a chained selection, e.g. `df["c"][mask] = v`, `df[mask]["c"] = v`, `df.loc[rows]["c"] = v`
  - `inplace`: `df["c"].method(..., inplace=True)` on a selected column
  - `datetime`: a datetime converted to an integer dtype (`astype("int64")` and similar names)
- The output is counts and `kind file:line` only. No source text was copied into this repository. Libraries: the latest wheel from PyPI on 2026-10-30. Repositories: default branch, shallow clone, at the commit listed below.
- It is a syntactic match. It does not know the type of the object, so it can match a non-pandas object (false positive) and it misses anything not written in these forms (false negative).

## Results

Libraries (`docs/census/libs.json`):

| package (wheel) | pandas files / files | LOC in pandas files | chained | inplace | datetime |
|---|---|---|---|---|---|
| dask 2026.8.0 | 54 / 184 | 33,214 | 0 | 0 | 0 |
| featuretools 1.31.0 | 77 / 293 | 8,182 | 0 | 0 | 0 |
| geopandas 1.2.0 | 19 / 32 | 17,326 | 0 | 0 | 0 |
| imbalanced-learn 0.14.2 | 3 / 57 | 2,052 | 0 | 0 | 0 |
| lifetimes 0.11.3 | 9 / 12 | 2,772 | 0 | 0 | 0 |
| mlxtend 0.25.0 | 10 / 119 | 1,706 | 0 | 0 | 0 |
| pandas-datareader 0.11.1 | 15 / 30 | 2,478 | 0 | 0 | 0 |
| pingouin 0.7.0 | 14 / 20 | 8,399 | 0 | 0 | 0 |
| plotly 7.1.0 | 3 / 1503 | 2,858 | 0 | 0 | 0 |
| scikit-learn 1.9.1 | 10 / 351 | 10,608 | 0 | 0 | 0 |
| seaborn 0.13.2 | 25 / 54 | 15,378 | 0 | 0 | 0 |
| sktime 1.2.0 | 374 / 1301 | 128,113 | 0 | 0 | 0 |
| statsmodels 0.15.0 | 98 / 453 | 90,633 | 0 | 0 | 0 |
| tsfresh 0.21.2 | 19 / 31 | 5,931 | 0 | 0 | 0 |
| xarray 2026.9.0 | 37 / 120 | 49,411 | 0 | 0 | 3 |
| yfinance 1.7.0 | 15 / 34 | 7,513 | 0 | 0 | 0 |

Teaching and application code (`docs/census/repos.json`):

| repository (commit) | pandas files / files | LOC | chained | inplace | datetime |
|---|---|---|---|---|---|
| jakevdp/PythonDataScienceHandbook (d66231454ef7) | 39 / 146 | 4,137 | 0 | 2 | 0 |
| ageron/handson-ml2 (7b7e23e72673) | 4 / 28 | 1,768 | 0 | 1 | 0 |
| ageron/handson-ml3 (ef1c9f5ab110) | 4 / 29 | 1,761 | 0 | 1 | 0 |
| wesm/pydata-book (a892791ce5a3) | 12 / 16 | 2,511 | 1 | 0 | 0 |
| fastai/fastbook (971f0289c3d0) | 3 / 46 | 511 | 0 | 0 | 0 |
| rasbt/machine-learning-book (63bee951ca45) | 22 / 70 | 5,866 | 0 | 0 | 0 |
| rasbt/python-machine-learning-book-3rd-edition (bf62496f44a9) | 20 / 64 | 5,154 | 0 | 0 | 0 |

## Precision: every hit was read

- 8 hits in total, all read by a person (the matching line, not the whole file).
- The 5 `chained`/`inplace` hits are real instances of the pattern: four are `df["column"].fillna(value, inplace=True)` in notebooks, one is `data.loc[data.three == 5]["three"] = 6`. Whether that code is wrong in a given notebook depends on its data and pandas version; we did not run them.
- The 3 `datetime` hits in xarray are false positives: two are `.dt.year/.month.astype(int)` (a calendar field, not a datetime converted to an integer timestamp) and one is a `np.round(` call.
- So: 5 of 8 hits are real patterns, 0 of 3 for the datetime pattern. Nothing here says how many hits are wrong in practice.

## What the numbers say, and what they do not

- The maintained libraries on this list contain none of the two Copy-on-Write patterns in their non-test code. Interpretation: maintained libraries have mostly already migrated, because their own test suites ran on pandas 3. This is the expected result and not a failure of the search.
- The few hits are in teaching notebooks. Interpretation: the remaining risk sits in downstream application code that has no such test suite and pins nothing; 7 repositories are a small, hand-picked sample of that and cannot say how large it is.
- This is not an estimate of how many projects are affected, and the tool does not claim a headline number. Its use case is the code we cannot sample here: your own functions, checked with your own inputs.
- The scan can be repeated: `python scripts/census.py DIR [DIR ...] --json out.json` (checked offline in `patchpilot/census_test.py`). Our own example `examples/ledger` gives `chained 1, inplace 1` by construction: we wrote those two sites.

## Second count: the first 20 repositories of GitHub's "pandas" topic (2026-10-31)

Same method and the same three patterns. The list rule was written before counting (`docs/census/PREREGISTERED2.txt`): the first 20 Python repositories on the GitHub topic page for pandas on 2026-10-31, minus pandas itself and the three already counted above (yfinance, seaborn, dask), leaving 16. Counts and `kind file:line` only, in `docs/census/repos2.json`; no source text was copied. Default branch, shallow clone, commit in brackets.

| repository (commit) | pandas files / files | LOC | chained | inplace | datetime |
|---|---|---|---|---|---|
| 30-Days-Of-Python (50c11a8) | 0 / 33 | 0 | 0 | 0 | 0 |
| abu (8a48f0c) | 95 / 299 | 22,606 | 0 | 17 | 0 |
| data-science-ipython-notebooks (5b3c00d) | 27 / 159 | 4,365 | 0 | 0 | 0 |
| datasets (62e0b42) | 13 / 157 | 16,501 | 0 | 0 | 0 |
| fg-data-profiling (0a8bf02) | 91 / 214 | 9,186 | 0 | 0 | 0 |
| ibis (8c3800b) | 44 / 206 | 35,305 | 0 | 0 | 0 |
| lux (972e5ec) | 33 / 73 | 5,065 | 0 | 0 | 0 |
| mlcourse.ai (df74e85) | 385 / 522 | 79,869 | 44 | 145 | 10 |
| modin (7ca200b) | 122 / 320 | 65,610 | 0 | 4 | 0 |
| orange3 (7ba04e1) | 10 / 426 | 6,839 | 0 | 0 | 0 |
| pandas-ai (bbbb771) | 19 / 100 | 1,846 | 0 | 0 | 0 |
| pygwalker (d91e207) | 20 / 112 | 2,106 | 0 | 0 | 0 |
| Sequoia-X (444c0db) | 8 / 18 | 616 | 0 | 0 | 0 |
| tqdm (9cf5a12) | 2 / 47 | 1,259 | 0 | 0 | 0 |
| tushare (0938569) | 22 / 52 | 6,972 | 0 | 0 | 0 |
| visidata (5f67ff8) | 3 / 276 | 478 | 0 | 0 | 0 |
| total | | | 44 | 166 | 10 |

Reading, with limits:
- 13 of the 16 repositories have no hit. The hits are in `mlcourse.ai` (course notebooks: 44 chained, 145 inplace, 10 datetime), `abu` (17 inplace, an application: quantitative trading), `modin` (4 inplace, all in one Kaggle stress-test script, not in the library) and nowhere else. These are syntactic matches; we did not run these projects.
- We read the 17 `abu` sites. Their enclosing code: 6 are in a method or a closure that uses object state (`self`), 1 is in a constructor, 4 are in a notebook, 4 are in demo functions of a script, and 2 are in one module-level function that takes a DataFrame (`calc_atr`). On our own small example of the same two forms, with pandas 2.3.3 and 3.0.6: `df["c"].fillna(other_series, inplace=True)` no longer fills (silent: a first value stays missing), and `fillna(method="bfill", inplace=True)` raises `TypeError` (loud). Both sites in that module-level function use the `method=` form, so it would raise on pandas 3 (loud, not silent), and PatchPilot repairs only silent breaks; we did not run it.
- What this means for the tool: in this sample the real hits sit mostly in methods that depend on object state, in notebooks and in scripts, not in pure functions that take JSON values or tables. That is outside what PatchPilot handles now (the Limitations list says so). We did not find a new silent break in a pure function; we did not look beyond these 16 repositories.

## Third count: pages 2 to 5 of the same topic list (2026-10-31)

Same method and patterns again. The rule was written before the count (`docs/census/PREREGISTERED3.txt`, list in `docs/census/pool3.txt`): pages 2 to 5 of the GitHub topic page for pandas on 2026-10-31, minus the four repositories already counted, 76 repositories; all 76 were cloned (shallow, default branch). Counts and `file:line` are in `docs/census/repos3.json`. Each site was then placed by `scripts/census_scope.py` into the kind of code that contains it (`docs/census/scope3.json`; the script prints names and parameter names of functions, no source text).

Result: 8 of 76 repositories have at least one site; 2 chained, 11 inplace, 7 datetime, 20 sites in all. Repositories with sites (the rest have none):

| repository | pandas files / files | chained | inplace | datetime | where the sites are |
|---|---|---|---|---|---|
| business-science/pytimetk | 70 / 87 | 0 | 1 | 0 | 1 function |
| graphistry/pygraphistry | 172 / 474 | 0 | 0 | 1 | 1 function |
| machow/siuba | 32 / 93 | 0 | 1 | 0 | 1 function |
| polyaxon/traceml | 7 / 68 | 0 | 3 | 0 | 3 function |
| ryfeus/lambda-packs | 336 / 24885 | 2 | 3 | 5 | 5 function, 5 method |
| stitchfix/hamilton | 43 / 113 | 0 | 1 | 1 | 2 function |
| unionai-oss/pandera | 47 / 274 | 0 | 1 | 0 | 1 method |
| wq/django-rest-pandas | 2 / 8 | 0 | 1 | 0 | 1 method |

Reading, with limits:
- `ryfeus/lambda-packs` holds vendored copies of old pandas source (10 of the 20 sites); they are not application code and are not interpreted. Of the other 10 sites in 7 repositories, 8 are inside a module-level function that takes arguments (the shape PatchPilot handles) and 2 are in methods.
- We read the lines of five of them. One is a false positive of the datetime pattern (`hamilton`, a week number cast to int, not a timestamp). Three are `column.method(..., inplace=True)` on a selected column inside functions that take a table or lists (`traceml` `clean_values`, `siuba` `complete`, `pytimetk` `create_recipe`); on pandas 3 such a call no longer writes into the table. `traceml` `clean_values` was then run through PatchPilot: `docs/REAL_PROJECT.md`, second project. One is a conversion of timestamps to int64 in `graphistry` that we did not examine further.
- These are syntactic matches in a sample of repositories ordered by GitHub's default, not a measure of how common the problem is. Whether each site changes a result was not checked here, except where `docs/REAL_PROJECT*.md` says a function was run.
