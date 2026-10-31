# One real project: indsl, before the maintainers' fix

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
- The patch is one line in the target function: it replaces the integer conversion of the index by a timedelta in seconds from the first timestamp. We read it; for a datetime index it gives the same values on both libraries and the same return type. We did not compare it with the maintainers' own fix, and we did not run the project's own test suite on it.

## Second run (same day, same function, same inputs)
Run again from the same manifest, for rehearsing the demo video: repaired, but in two attempts. Attempt 1 (13,574 tokens) was rejected at the visible tests, so hidden and differential were not reached; attempt 2 (13,478 tokens) passed all three gates, differential PASS with 142 valid inputs of 200 and 0 divergences. 27,052 tokens in total, 362.8 s for the whole scan (342.4 s for the repair). The accepted patch again replaces the integer conversion of the index by a timedelta in seconds. The first run needed one attempt and 13,501 tokens (194.0 s), so the same model on the same function took one and two attempts: two runs, not a rate. Nothing was applied to the clone.

## What it does not show
- One function in one project, chosen because the break was known, run twice. No other project was run.
- The input is ours (five timestamps), not recorded from the project's tests; the hidden inputs are derived by our generator from it.
- The environments hold the dependencies we installed for this run; for a project with more dependencies the same steps are needed.
- Getting to this result took five fixes in our own tool, all found by running on this project (a circular import in the runner, copying test-looking module names, an `ImportError` message that hid the module name, a serializer that failed on arrays, and pytest missing from the environments); they are in `docs/engineering-log.md`.
