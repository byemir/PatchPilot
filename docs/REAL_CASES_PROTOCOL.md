# Protocol for adding cases from third-party code

Written on 2026-10-29 before any candidate was searched or looked at. Purpose: the next cases come from code we did not write, chosen by fixed rules, not by whether a model solves them.

## Inclusion criteria (all required)

1. The behavior change is documented in the official pandas 3.0.0 or NumPy 2.0.0 release notes. We record the URL and the quoted sentence.
2. The code is under MIT, BSD or Apache-2.0, checked in the LICENSE file at the commit we copy from.
3. The function (or a short chain of helpers) sits in one file, can be extracted verbatim by script (ast), and depends only on the standard library and the library under repair. Anything we add (an adapter for JSON input and output) is thin and marked as ours.
4. The project itself fixed the problem (closed issue or merged pull request). We copy the code from the parent of the fix commit, so the code existed before this project and is not edited by us.
5. The output is deterministic on the old library for fixed inputs (two runs equal).
6. The breakage is silent on the new library: no exception on our inputs, different output.
7. The inputs are fixed before any model sees the case and are not changed afterwards. They exercise the documented change; they are not chosen to make a model fail or succeed.

## Search method

- Tool: `gh search issues --state closed --language python --limit 30` on public GitHub, run by `scripts/real_case_search.sh` with exactly these six queries:
  - Q1 `"chained assignment" "pandas 3"`
  - Q2 `"copy-on-write" "pandas 3"`
  - Q3 `"pandas 3.0" astype datetime`
  - Q4 `"numpy 2" "NEP 50"`
  - Q5 `"numpy 2.0" uint8 overflow`
  - Q6 `"pandas 3" "str dtype"`
- Hits are examined in the order the search returns them (best match). Every examined hit goes into `docs/real_cases/candidates.md` with a decision and the first criterion it failed. Hits are not skipped because they look uninteresting or too easy. The raw search output is committed.
- Stop when 3 cases are accepted or when the time box ends (31 October 2026, evening), whichever comes first.

## Acceptance

A candidate becomes a case only if `patchpilot.validate_case` passes: old library OK, new library SILENT_BREAKAGE, tests green on both, hidden inputs behave the same way, and a known-bad patch is rejected. A candidate that fails is not counted but stays in the table with the reason.

## Reporting

- Third-party cases and our own reproductions get separate labels in the README and in the results tables.
- Each third-party case lists source URL, license, commit hash and the release-note quote, and carries the upstream notice in `docs/THIRD_PARTY_NOTICES.md`.
- Candidates that did not pass are shown in the table.
- No model is run on a candidate before it is accepted.
