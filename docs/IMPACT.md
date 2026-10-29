# Why this matters, and what this repository does and does not show

Every number below has a source. Interpretation is marked as such.

## The problem is documented by the libraries themselves

The pandas 3.0.0 release notes (`doc/source/whatsnew/v3.0.0.rst` at tag v3.0.0, section "Datetime/timedelta resolution inference") say about the new default resolution: "One big exception is converting to integers, which will give integers 1000x smaller." Code that does this keeps running; it returns numbers that are 1000 times smaller. `docs/CASES.md` quotes the release-note sentence behind each case.

## The ecosystem is large

Downloads of the two libraries in the 30 days before 2026-10-29 (pypistats.org API, `/api/packages/<name>/recent`, fetched 2026-10-29): pandas 546,920,076; numpy 802,155,590. These counts include CI runs and mirrors, so they are not a user count. Interpretation: a behavior change in either library reaches a very large number of installs, and most of the affected code is not in well-tested public libraries.

## Projects are fixing these breaks by hand

A fixed set of six keyword queries (`docs/real_cases/search_20261029_run2/queries.tsv`), 30 results each, over GitHub pull requests and issues about pandas 3.0 and NumPy 2.0 changes, returned 168 distinct hits in 128 repositories (142 pull requests, 26 issues). 93 of the hits (79 repositories) are in repositories with an MIT, BSD or Apache-2.0 license (`repos.tsv`). This is one keyword search, not a census: it does not say how many of the changes were silent, and most hits are not.

Of those hits, twelve finalists were read in detail (`docs/real_cases/candidates.md`): ten were rejected after reading their code, with the reason for each listed there, and two met all selection rules and became benchmark cases (indsl, Kythera). Interpretation: the selection rules (one self-contained file, deterministic, silent, permissive license) filter out most real-world cases, which is also a statement about where this tool applies.

## What you can do with it today

    python -m patchpilot.repair my_module.py my_function --inputs probes.json --lib pandas --endpoint http://127.0.0.1:8080/v1

One function in one file, your own inputs, a local open-weight model, a patch that has passed three gates and a diff you review before `--apply`. Measured on a real function from scikit-FIBERS: one run, accepted on the first attempt, 2230 tokens, 38 s for the repair on one Apple M2 Ultra. See "Try it on your own function" in the README.

## What this does not show

- It has not been run on whole repositories; it works on one function at a time.
- Of 16 case folders, 12 are the main benchmark (11 synthetic, 1 from real code) and 4 are two third-party cases in two variants. The two third-party cases are the same documented change (datetime resolution), so they are two examples of one mechanism.
- In the third-party runs with the adapter editable, the model changed the third-party function in only 3 of 10 runs; with the adapter read-only all 10 changed it. Two of the 10 read-only patches check the pandas version and are wrong for nanosecond data (README, "Cases from third-party code").
- The differential check was too thin (WEAK) on one of the two third-party cases.
- Everything ran on one machine, with small samples (5 runs per setting).
