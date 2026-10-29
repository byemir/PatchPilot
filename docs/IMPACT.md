# Why this matters, and what this repository does and does not show

Every number below has a source. Interpretation is marked as such.

## The problem is documented by the libraries themselves

The pandas 3.0.0 release notes (`doc/source/whatsnew/v3.0.0.rst` at tag v3.0.0, section "Datetime/timedelta resolution inference") say about the new default resolution: "One big exception is converting to integers, which will give integers 1000x smaller." Code that does this keeps running; it returns numbers that are 1000 times smaller. `docs/CASES.md` quotes the release-note sentence behind each case.

## The ecosystem is large

Downloads of the two libraries in the 30 days before 2026-10-29 (pypistats.org API, `/api/packages/<name>/recent`, fetched 2026-10-29): pandas 546,920,076; numpy 802,155,590. These counts include CI runs and mirrors, so they are not a user count. Interpretation: a behavior change in either library reaches a very large number of installs, and most of the affected code is not in well-tested public libraries.

## Projects are fixing these breaks by hand

A fixed set of six keyword queries (`docs/real_cases/search_20261029_run2/queries.tsv`), 30 results each, over GitHub pull requests and issues about pandas 3.0 and NumPy 2.0 changes, returned 168 distinct hits in 128 repositories (142 pull requests, 26 issues). 93 of the hits (79 repositories) are in repositories with an MIT, BSD or Apache-2.0 license (`repos.tsv`). This is one keyword search, not a census: it does not say how many of the changes were silent, and most hits are not.

Of those hits, twelve finalists were read in detail (`docs/real_cases/candidates.md`): ten were rejected after reading their code, with the reason for each listed there, and two met all selection rules (indsl, Kythera). Their code is not in this repository; `o1` and `o2` are our own functions for the same documented mechanism. Interpretation: the selection rules (one self-contained file, deterministic, silent, permissive license) filter out most real-world cases, which is also a statement about where this tool applies.

## What you can do with it today

    python -m patchpilot.repair my_module.py my_function --inputs probes.json --lib pandas --endpoint http://127.0.0.1:8080/v1

One function in one file, your own inputs, a local open-weight model, a patch that has passed three gates and a diff you review before `--apply`. The example function `examples/own_function/subject_dropout.py` is also the benchmark case o3 (README, "Results on o1, o2 and o3"); the one-command tool was run end to end once on it with the local model: accepted on the first attempt, 2025 tokens, 32 s for the repair (one run, not a rate). An earlier measurement was made on a function from another project that is no longer in the repository and is not quoted here.

## What this does not show

- It has not been run on whole repositories; it works on one function at a time.
- All 14 case folders are small functions we wrote, derived from documented library changes. None is code taken from a real project, so success on them says nothing about how often real code is fixed. o1 and o2 are the same documented mechanism (datetime resolution), o3 is the same as p5 and p8 (chained assignment).
- Models solved all 75 runs on o1, o2 and o3, so these cases show coverage, not difficulty.
- Everything ran on one machine, with small samples (5 runs per setting).
