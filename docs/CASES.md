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

## o1_elapsed_seconds, o2_bars_epoch_seconds, o3_subject_dropout (pandas 2.3 to 3.0), code written by us
- Source: the three functions were written for this project (`scripts/build_own_cases.py`; o3 is `examples/own_function/subject_dropout.py`). They replace earlier cases built from functions copied from three open-source projects, which were removed so that the repository contains no code from other projects.
- o1 and o2: the documented change is the pandas 3.0 datetime resolution inference (release note quoted in the section on p1 and in `docs/IMPACT.md`): "One big exception is converting to integers, which will give integers 1000x smaller." o1 converts a `DatetimeIndex` with `np.array(index, dtype=np.int64)` and divides by 1e9; o2 converts a column with `astype("int64") // 10**9`. Both run without error and return numbers 1000x smaller.
- o3: a seeded random choice (standard library `random`) of subjects to drop and a chained assignment `table["observed"].iloc[position] = 0`; on pandas 3 (copy-on-write) the write is lost and the flags stay 1. Same documented change as p5.
- Validation (`validate_case`): all three VALID, known_good accepted. The new library differs from the old on 4 of 4 (o1), 3 of 3 (o2) and 4 of 4 (o3) visible probes and on all held-out probes (8 each, chosen from 141, 160 and 138 reproducible candidates; 113, 143 and 127 of those separate the libraries). known_bad: o1 `hardcode_microseconds` rejected at visible; o2 `hardcode_microseconds` at visible and `branch_on_version` at hidden (a constructed patch that divides by 10**6 on pandas 3: right for microsecond data, wrong for nanosecond input); o3 `chained_row` and `first_rows_only` at visible.
- Measurements (effort low, re-scored at seed 1): muse-glimmer (local) 15 runs per case, 15/15 solved on each, first try 14, 15 and 15, avg tokens 1543, 1849 and 2055 (`results/bench_20261029-191802_muse-glimmer_local.json`); muse-spark-1.3 5 runs per case, all first try, avg 2120, 3099, 2130 (`bench_20261029-201532_muse-spark-1.3.json`); muse-wonder-1.0 5 per case, all first try, avg 1997, 2114, 2221 (`bench_20261029-202129_muse-wonder-1.0.json`). All 75 runs re-scored PASS. Patches not read; token counts only.

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

## q1_score_aliases, q2_epoch_with_gaps, q3_scalar_repr (code written by us; incomplete fixes pass the visible inputs)
- q1 (pandas 2.3 to 3.0): `low = frame["score"]; low[low < floor] = floor` and the same for a cap. On pandas 3 (copy-on-write) writes through such a variable do not change the frame (pandas 3.0.0 release notes, "Consistent copy/view behaviour with Copy-on-Write"). Visible inputs exercise the floor only; held-out inputs also exceed the cap, so a patch that repairs only the floor passes visible and fails hidden.
- q2 (pandas 2.3 to 3.0): `stamps.astype("int64") // 10**9` after `pd.to_datetime`, gaps kept as None; same documented change as o1 and o2. Held-out inputs (written by hand) contain UTC-offset timestamps, nanosecond strings, None values and microsecond strings with six fractional digits. Rejected at hidden: `branch_on_version` (divides by 10**6 on pandas 3) and `subtract_epoch` (subtracting `pd.Timestamp("1970-01-01")` raises for offset timestamps); `hardcode_microseconds` at visible.
- q3 (NumPy 1.26 to 2.x): `f"{values.max()!r}"`; NumPy 2 changed the scalar repr (NEP 51: `np.float64(3.25)`). Visible inputs are float columns only; held-out inputs have integer, boolean and large/small float columns. `float_cast` (right for floats, `3` becomes `3.0`) is rejected at hidden.
- Validation: all three VALID, known_good accepted; known_bad rejected at: q1 `floor_only` hidden, `cap_only` visible; q2 `branch_on_version` and `subtract_epoch` hidden, `hardcode_microseconds` visible; q3 `float_cast` hidden. Held-out inputs were written by hand, not derived by the generator.
- Measurements (effort low, re-scored at seed 1): muse-glimmer (local) 15 runs per case: q1 15/15 (15 first try, avg 1231 tokens), q2 14/15 (9, 2526), q3 13/15 (3, 2192); muse-spark-1.3 5 per case, all solved on the first attempt (avg 1753, 3600, 1644); muse-wonder-1.0 5 per case, all solved, first try 5, 3, 5 (avg 1453, 3763, 1242). Files: bench_20261029-210614, -215819, -220335. Attempts rejected at the hidden check: Glimmer q2 9, q3 18; Wonder q2 2 (from the local attempt files).

## Real incidents (no code taken)

Candidates were chosen from GitHub pull requests and issues by the rules in `docs/REAL_CASES_PROTOCOL.md`; the log is `docs/real_cases/candidates.md`. Two candidates met all rules and were first built as benchmark cases from the upstream code (cognitedata/indsl pull request 639, ziagl888/Kythera pull request 229, both fixing the datetime-resolution change). Those cases and their results were removed from the repository so that it holds only our code; o1 and o2 above are our own functions for the same documented mechanism, not copies.
