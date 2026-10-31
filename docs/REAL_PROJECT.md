# Two real projects: indsl (before the maintainers' fix) and traceml (found by a scan)

What this is: PatchPilot's project mode (README, "Functions that import their siblings") run once on a function of a real, third-party project, at the commit before the maintainers fixed it. What it is not: a rate, a survey, or a claim about how many projects work this way. The files are in `examples/real_project_indsl/` (our manifest, our one input, the numbers). No code from indsl is in this repository.

## Why this project
It came out of the keyword search in `docs/IMPACT.md` (pull request 639, "fix/pandas3-datetime-index-to-int64", Apache-2.0). It was chosen because we already knew the break was silent from reading the pull request, so this is not a random sample. Earlier, a one-file version of this function had been built as a benchmark case; that case was removed from the repository so that it holds no third-party code.

## What was run (2026-10-31, Mac Studio M2 Ultra)
1. `git clone` of the project and `git checkout fab55f6` (the parent of the merge). The clone is in `/tmp`, outside this repository, and nothing was written to it (no `--apply`).
2. Two virtual environments with the project's own dependencies: pandas 2.3.3 and pandas 3.0.6, both with numpy 2, scipy 1.17, typeguard 4, packaging, pywavelets and pytest.
3. A manifest with `"root"`, `"old"` and `"new"` for the one target and one input we wrote: a five-point series with timestamps (`examples/real_project_indsl/`).
4. `python -m patchpilot.scan scan.json --triage-only`, then the same without `--triage-only` and with `--endpoint` for the local Muse Glimmer (effort low, up to three attempts).

## Result (one run)
- Check: `silent`. On pandas 2.3.3 the function returns the elapsed seconds `[0, 3600, 9000, 10800, 18000]`; on pandas 3.0.6 it returns values around -1.7e9, without any error (the index has microsecond resolution there, and the code mixes it with a nanosecond `Timestamp.value`). We also called the function directly, outside PatchPilot, in both environments and got the same two results.
- Repair: accepted on the first attempt, 13,501 tokens, 194.0 s (the model also sees the other modules of the project as read-only context, which is why this costs more than our small examples). Visible tests, hidden tests and the differential check all passed; the differential check generated 200 inputs, 142 valid, 0 divergences.
- The patch is one line in the target function: it replaces the integer conversion of the index by a timedelta in seconds from the first timestamp. We read it; for a datetime index it gives the same values on both libraries and the same return type. We did not compare it with the maintainers' own fix, and the project's own tests are in the last section.

## Second run (same day, same function, same inputs)
Run again from the same manifest, for rehearsing the demo video: repaired, but in two attempts. Attempt 1 (13,574 tokens) was rejected at the visible tests, so hidden and differential were not reached; attempt 2 (13,478 tokens) passed all three gates, differential PASS with 142 valid inputs of 200 and 0 divergences. 27,052 tokens in total, 362.8 s for the whole scan (342.4 s for the repair). The accepted patch again replaces the integer conversion of the index by a timedelta in seconds. The first run needed one attempt and 13,501 tokens (194.0 s), so the same model on the same function took one and two attempts: two runs, not a rate. Nothing was applied to the clone.

## What it does not show
- One function in one project, chosen because the break was known, run twice. No other project was run.
- The input is ours (five timestamps), not recorded from the project's tests; the hidden inputs are derived by our generator from it.
- The environments hold the dependencies we installed for this run; for a project with more dependencies the same steps are needed.
- Getting to this result took five fixes in our own tool, all found by running on this project (a circular import in the runner, copying test-looking module names, an `ImportError` message that hid the module name, a serializer that failed on arrays, and pytest missing from the environments); they are in `docs/engineering-log.md`.

# Second project: polyaxon/traceml, a function the scan flagged

Unlike indsl, this function was not chosen because someone had reported it. The static count in `docs/CENSUS.md` (third count) flagged three `column.fillna(..., inplace=True)` sites in `traceml/processors/importance_processors.py`; the function `clean_values(params, metrics)` takes lists of records and numbers and returns two tables. We did not know whether it changed a result, and we did not look for a maintainer fix. Files: `examples/real_project_traceml/` (our manifest, our two inputs, the numbers). No traceml code is in this repository.

## What was run (2026-10-31, same Mac)
1. `git clone --depth 1` of `polyaxon/traceml` (Apache-2.0) into `/tmp`, commit `2452c1a8f2be742a8a3b8e379568a6ce3bf4394c` (the default branch that day; the commit is dated 2026-10-21). Nothing was written into the clone (no `--apply`).
2. Two virtual environments, pandas 2.3.3 and 3.0.6, each with NumPy 2, `clipped` (its only import besides pandas and NumPy) and pytest.
3. A manifest with `"root"`, `"old"` and `"new"`, and two inputs written by us: four and five parameter records with missing numeric values, and a list of metrics.
4. `scan --triage-only`, then `scan` with the local Muse Glimmer (effort low), started with a clean environment (`env -i`).

## Result (one run)
- Check: `silent`, on 2 of 2 inputs, nothing raised. On pandas 2.3.3 the missing parameter values are replaced by the column mean; on 3.0.6 they stay `NaN` (a call of the form `df["c"].fillna(mean, inplace=True)` no longer writes into the table).
- Repair: accepted on the first attempt, 4,019 tokens, 54.8 s. Visible tests, hidden tests and the differential check passed; the differential generated 200 inputs, 152 valid, 0 divergences. We read the diff: it assigns the result of `fillna` back to the column instead of filling in place, and the logic is otherwise unchanged. We did not compare it with any maintainer change; the project's own tests are in the last section.

## What it does not show
- One function in one project, one run. The static count found 10 sites in 7 non-vendored repositories; this is the only one we ran. It is not an estimate of how many projects have such breaks.
- The inputs are ours and numeric only. The function also fills text columns (`dtype == "object"`); pandas 3 stores text as a new string type, so that branch may behave differently, and we did not test it.
- Whether the maintainers consider this a defect, or support pandas 3 yet, was not checked. We reported the finding to the project as an issue on 2026-10-31 (https://github.com/polyaxon/traceml/issues/33); no reply had arrived when this was written.


# The projects' own tests, with and without the patches (2026-10-31)

Same Mac, on copies of the two clones in `/tmp` (the clones themselves were not changed). The accepted diffs were applied with `patch`; the same tests were run before and after, in the pandas 2.3.3 and the pandas 3.0.6 environments.

| project | tests run | pandas 2.3.3, without / with patch | pandas 3.0.6, without / with patch |
|---|---|---|---|
| traceml | `traceml/tests/test_events_processing/test_importance_processors.py` (8 tests) | 8 passed / 8 passed | 8 passed / 8 passed |
| indsl | `tests/data_quality/test_out_of_range.py` and `test_studentised_residuals.py` (7 tests; they call the two public functions that use the patched helper) | 7 passed / 7 passed | 7 passed / 7 passed |

What this shows: the patches do not break the project's own tests on either pandas version, and these tests did not catch the silent break on pandas 3 (they pass without the patch), which is the situation PatchPilot is meant for. In the traceml run the number of warnings fell from 9 to 3 with the patch (the chained-assignment warnings are gone).

What it does not show: we ran only the test files named above, not the whole test suites. The test environments lack some of the projects' optional dependencies (for example `statsmodels` for indsl), so the full suites cannot be run there; before this run, 4 of the 8 traceml tests failed on both pandas versions only because `scikit-learn` was missing, so we installed `scikit-learn` 1.9.1 into the two traceml environments. We did not check that the indsl tests reach the patched line. Two functions in two projects, not a rate.
