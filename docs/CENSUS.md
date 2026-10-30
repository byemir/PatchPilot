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
