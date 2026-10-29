# Cases p5, p6, n8 and their sources

These three cases are our own reproductions derived from documented behavior changes. They are not incidents from real projects. p2, p3 and p4 also have no real project incident behind them (p3's source is the deprecation text, not a 3.0.0 release-note line).

## p5_chained_assignment (pandas 2.3 to 3.0)
- Pattern: `df["amount"][mask] = value` (chained assignment) in `apply_discounts`. Old library modifies `df`; new library does not modify `df` and emits only a `ChainedAssignmentError` warning (a `Warning` subclass, so no exception; measured on pandas 3.0.6).
- Source: pandas 3.0.0 release notes, "Consistent copy/view behaviour with Copy-on-Write": chained assignment "will stop working"; `SettingWithCopyWarning` is removed. https://pandas.pydata.org/docs/whatsnew/v3.0.0.html (the page does not mention `ChainedAssignmentError`).

## p6_str_dtype_checks (pandas 2.3 to 3.0)
- Pattern: `df[col].dtype == object` and `v is None` in `clean_labels`.
- Source: pandas 3.0.0 release notes, "Dedicated string data type by default": strings are inferred as `str` instead of `object`, the missing value sentinel is always `NaN`, and this can break code "checking for the `.dtype` being object dtype or checking the exact missing value sentinel". https://pandas.pydata.org/docs/whatsnew/v3.0.0.html (the migration guide was not read).

## n8_string_to_bool (NumPy 1.26 to 2.x)
- Pattern: `np.array(flags).astype(bool)` with string flags such as "0".
- Source: NumPy 2.0.0 release notes, "Truthiness of NumPy strings changed" (gh-23871): strings are True when non-empty; "0" is now True. https://numpy.org/devdocs/release/2.0.0-notes.html ("False" is not named on the page; that it becomes True follows from the non-empty rule).

## Validation
validate_case: all three VALID (known_good accepted; known_bad rejected at visible, hidden or differential gates).

## Measurements (counted, effort=low, 5 runs per cell, one-shot, accepted patches re-scored at seed 1)

| case | model | solved | first try | avg tokens |
|---|---|---|---|---|
| p5 | muse-spark-1.3 | 5/5 | 5 | 1407 |
| p5 | muse-wonder-1.0 | 5/5 | 5 | 1511 |
| p5 | muse-glimmer (local) | 5/5 | 4 | 1493 |
| p6 | muse-spark-1.3 | 5/5 | 5 | 2610 |
| p6 | muse-wonder-1.0 | 5/5 | 5 | 2326 |
| p6 | muse-glimmer (local) | 5/5 | 4 | 2210 |
| n8 | muse-spark-1.3 | 5/5 | 5 | 2807 |
| n8 | muse-wonder-1.0 | 5/5 | 5 | 2553 |
| n8 | muse-glimmer (local) | 5/5 | 1 | 2772 |

All 45 runs solved and re-scored PASS. These cases did not separate the three models (n=5 per cell), so they add breadth, not difficulty. For n8, Glimmer needed a second attempt in 4 of 5 runs; why was not checked (patches not read). Token counts only, no dollar cost.

Result files: results/bench_20261029-0757*..0804* (hosted, six files) and results/bench_20261029-052208, -052424, -052806 (muse-glimmer_local).

## p7_censor_chained_iloc (pandas 2.3 to 3.0), code from a real project
- Source: the function `censor` and the import lines above it are copied verbatim (lines 1 to 5 and 226 to 245) from scikit-FIBERS, src/skfibers/simulators/SIM1.py at commit 356c6d5, MIT license (Copyright (c) 2023 Ryan Urbanowicz; text in docs/THIRD_PARTY_NOTICES.md). https://github.com/UrbsLab/scikit-FIBERS
- Pattern: `df['Censoring'].iloc[index] = choice` (chained assignment). The project's issue #19 reports that under pandas 3 this write is lost; its fix commit ee81b24 replaces it with `df.loc[index, 'Censoring'] = choice` and removes the `pd.options.mode.chained_assignment = None` line from the simulators (issue closed by PR #20 on 2026-09-14, as read from the issue page).
- Written by us: the wrapper `censor_records` (maps the seed to 1..1000 so every run is seeded; `censor` does not seed for 0 or None), the visible test, inputs, known_good and known_bad. The project's own tests were not used.
- Validation: VALID; the new library (pandas 3.0.6) differs from the old (2.3.3) on 4 of 4 visible and 4 of 5 hidden probes (the fifth has censoring_frequency 0.0). known_bad: `chained_row` rejected at visible, `only_zero_writes` rejected at differential.
- Measurements (effort low, 5 runs per model, re-scored at seed 1): muse-spark-1.3 5/5, first try 5, avg 3378 tokens; muse-wonder-1.0 5/5, 5, 2760; muse-glimmer (local) 5/5, 5, 2502. Model patches not compared with the project's fix.

## p8_session_report_three_breaks (pandas 2.3.3 to 3.0.6), three silent breaks in one function
Our own reproduction (not project code). `session_report` combines three documented pandas 3 changes, each changing a different part of the output:
- Epoch seconds: `df["ts"].astype("int64") // 10**9` on datetimes parsed from strings gives integers 1000x smaller. Source: pandas 3.0.0 release notes, "Datetime/timedelta resolution inference": "The new default resolution when parsing strings is microseconds" and "One big exception is converting to integers, which will give integers 1000x smaller." https://pandas.pydata.org/docs/whatsnew/v3.0.0.html
- Flag column: `df["flag"][big] = "large"` is a chained assignment and no longer modifies `df` (same source as p5; pandas 3.0.6 emits only a `ChainedAssignmentError` warning).
- Null notes: `v is None` finds no nulls because the missing value sentinel of the `str` dtype is `NaN` (same source as p6).
- Validation: VALID; the new library differs on 4 of 4 visible and 5 of 5 hidden probes; known_good accepted; known_bad `flag_still_chained` rejected at visible, `empty_note_missing` at hidden, `version_specific_unit` (divides by 10**6) at visible.

## n9_fleet_report_three_breaks (NumPy 1.26.4 to 2.5.4), three silent breaks in one function
Our own reproduction (not project code). `fleet_report` combines three NumPy 2 changes:
- String flags: `astype(bool)` on strings, "0" becomes True. Source: NumPy 2.0.0 release notes, "Truthiness of NumPy strings changed" (gh-23871). https://numpy.org/devdocs/release/2.0.0-notes.html
- `np.uint8(level) + 100`: 300 on 1.26.4 and 44 (wrapped) on 2.5.4 for level 200; and `np.float32(level) * gain` plus a float32 running total: results differ at the sixth decimal (24.69134 versus 24.691339). The release notes say only that NEP 50 type promotion was adopted and "can lead to changes in output dtypes and lower precision results for mixed-dtype operations"; the specific values above were measured by us on these two versions, not quoted from the notes.
- Validation: VALID; the new library differs on 4 of 4 visible and 4 of 5 hidden probes (the fifth is an empty device list); known_good accepted; known_bad `flag_equals_one`, `wrap_mod_256` and `total_still_float32` rejected at visible, `not_zero_string` at hidden.

## Measurements p8 and n9 (counted, effort low, 5 runs per cell, one-shot, re-scored at seed 1)
- p8: muse-spark-1.3 5/5, first try 5, avg 3125 tokens; muse-wonder-1.0 5/5, 5, 2354; muse-glimmer (local) 5/5, 5, 2495.
- n9: muse-spark-1.3 5/5, first try 5, avg 3149; muse-wonder-1.0 5/5, 5, 2515; muse-glimmer (local) 3/5, first try 2, avg 5222.
- All 28 solved runs re-scored PASS. Model patches not read; token counts only.
