# Why this matters, and what this repository does and does not show

Every number below has a source. Interpretation is marked as such.

## The problem is documented by the libraries themselves

The pandas 3.0.0 release notes (`doc/source/whatsnew/v3.0.0.rst` at tag v3.0.0, section "Datetime/timedelta resolution inference") say about the new default resolution: "One big exception is converting to integers, which will give integers 1000x smaller." Code that does this keeps running; it returns numbers that are 1000 times smaller. `docs/CASES.md` quotes the release-note sentence behind each case.

## The ecosystem is large

Downloads of the two libraries in the 30 days before 2026-10-29 (pypistats.org API, `/api/packages/<name>/recent`, fetched 2026-10-29): pandas 546,920,076; numpy 802,155,590. These counts include CI runs and mirrors, so they are not a user count. Interpretation: a behavior change in either library reaches a very large number of installs, and most of the affected code is not in well-tested public libraries.

## Projects are fixing these breaks by hand

A fixed set of six keyword queries (`docs/real_cases/search_20261029_run2/queries.tsv`), 30 results each, over GitHub pull requests and issues about pandas 3.0 and NumPy 2.0 changes, returned 168 distinct hits in 128 repositories (142 pull requests, 26 issues). 93 of the hits (79 repositories) are in repositories with an MIT, BSD or Apache-2.0 license (`repos.tsv`). This is one keyword search, not a census: it does not say how many of the changes were silent, and most hits are not.

Of those hits, twelve finalists were read in detail (`docs/real_cases/candidates.md`): ten were rejected after reading their code, with the reason for each listed there, and two met all selection rules (indsl, Kythera). Their code is not in this repository; `o1` and `o2` are our own functions for the same documented mechanism. Interpretation: the selection rules (one self-contained file, deterministic, silent, permissive license) filter out most real-world cases, which is also a statement about where this tool applies.

## How common are the patterns? A static count

`docs/CENSUS.md` counts three pandas-3 patterns in 115 public repositories in four counts, each list fixed before counting and every result reported: 16 libraries (0 real hits, 3 false positives), 7 teaching repositories (5 real pattern instances, in notebooks), the first 20 repositories of GitHub's pandas topic (13 of 16 new ones without a hit; the hits are in course notebooks, in one application and in one stress-test script) and pages 2 to 5 of the same list (8 of 76 with a site; leaving out one repository that holds a vendored copy of pandas, 10 sites in 7 repositories, 8 of them inside module-level functions that take arguments, the shape PatchPilot handles). Interpretation: maintained libraries have already migrated; the remaining sites sit in application code, notebooks and methods, and in some pure functions. These are syntactic matches, a count of patterns, not of broken programs, in repositories ordered by GitHub's default.

## Real projects, an upstream report, and an independent test

- indsl (a known break, at the commit before its maintainers' fix) and polyaxon/traceml (a function our static count flagged, not known to be broken): both were classified silent and repaired with all three gates passed (`docs/REAL_PROJECT.md`). The projects' own tests pass on pandas 2.3.3 and 3.0.6 with and without the patch (traceml 8 of 8, indsl 7 of 7), so those tests did not catch the break and the patches did not break them. The traceml finding was reported to the project as an issue (https://github.com/polyaxon/traceml/issues/33). One function per project, our inputs.
- Through the whole chain on traceml (`discover`, `propose`, `scan` with Muse Spark Open), with the model choosing the inputs: at effort low, six of six patches were rejected by the gates; at effort medium the third patch passed all three gates (`docs/APP_RUNS.md`). The gates stopped patches that fit the proposed inputs but changed behavior elsewhere.
- Independent test (pre-registered, `docs/HELDOUT.md`): the chain on eight census projects we had not tuned on. `discover` listed 11 runnable functions in 4 projects; none could be classified, because all 11 needed libraries outside the pinned environments. The limit on foreign code is the dependency environment, not the model or the gates. A follow-up on one project, written after the result and labelled as exploratory, classified 3 of its 6 functions (2 healthy, 1 loud that we read as an input artefact).
- Interpretation: there is evidence that the method finds and repairs a real silent break and that the gates reject wrong patches; there is no evidence about how often real code is affected or repaired. We make no claim of a rate.


## Tables as inputs

Most pandas code takes a DataFrame, not a JSON object. The scan, the repair gates and `capture` now accept a table written as `{"$df": {column: [values]}}` (README, "DataFrames as input and output"). `examples/frames/` has six notebook-style functions we wrote, three with the patterns counted in `docs/CENSUS.md`; its manifest and inputs were recorded from the project's own tests. Offline, with scripted replies, the three silent breaks are repaired behind the gates. No real model run is recorded yet. Results are compared by values, column names and index, not by dtype.

## Functions that import their siblings

Most of the real candidates we rejected depended on other modules of their project. A manifest target can now carry `"root"` (README, "project mode"): the function is run and repaired inside a copy of its project folder, the model may edit only the target file. `examples/project` shows it with scripted replies. It was run once on a third-party project, indsl at the commit before its maintainers' fix: Check found the silent break, the local Glimmer repaired it (first attempt in one run; in a second run the visible tests rejected the first patch and the second passed all three gates) (`docs/REAL_PROJECT.md`; one function, chosen because the break was known, not a rate). A second project, polyaxon/traceml, was run after the static count flagged one of its functions (third count in `docs/CENSUS.md`): there the break was not known beforehand, Check found it on 2 of 2 inputs and the local Glimmer repaired it on the first attempt behind all three gates (`docs/REAL_PROJECT.md`; one function, our inputs, not a rate). A project whose package imports libraries outside the interpreters you name is reported as `invalid`.

## A gate for pull requests

`python -m patchpilot.scan scan.json --triage-only --fail-on-silent` exits with code 1 when a listed function changes silently on the new library. No model and no API key are used. `docs/ci-example.yml` is an example GitHub Actions workflow (it is in `docs/`, so it is not active, and it was not run on GitHub).

## What you can do with it today

    python -m patchpilot.repair my_module.py my_function --inputs probes.json --lib pandas --endpoint http://127.0.0.1:8080/v1

One function in one file, your own inputs, a local open-weight model, a patch that has passed three gates and a diff you review before `--apply`. The example function `examples/own_function/subject_dropout.py` is also the benchmark case o3 (README, "Results on o1, o2 and o3"); the one-command tool was run end to end once on it with the local model: accepted on the first attempt, 2025 tokens, 32 s for the repair (one run, not a rate). An earlier measurement was made on a function from another project that is no longer in the repository and is not quoted here.

## What this does not show

- It has not been run on whole repositories; it works on one function at a time.
- The 17 case folders are small functions we wrote, derived from documented library changes, so success on them says nothing about how often real code is fixed. The real-project evidence is two functions in two projects (indsl and traceml, below), one run set each. o1 and o2 are the same documented mechanism (datetime resolution), o3 is the same as p5 and p8 (chained assignment).
- Models solved all 75 runs on o1, o2 and o3, so these cases show coverage, not difficulty.
- On q1 to q3 (visible inputs allow a partial fix) 29 first-pass attempts were rejected by the hidden check, which a visible-tests-only workflow would have accepted; local Glimmer solved 42 of 45 runs there, hosted models 30 of 30 (README, "Results on q1, q2 and q3").
- Everything ran on one machine, with small samples (5 runs per setting).
