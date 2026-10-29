# Cases p5, p6, n8 and their sources

These three cases are our own reproductions derived from documented behavior changes. They are not incidents from real projects. p2, p3 and p4 also have no real project incident behind them (p3's source is the deprecation text, not a 3.0.0 release-note line).

## p5_chained_assignment (pandas 2.3 to 3.0)
- Pattern: `df["amount"][mask] = value` (chained assignment) in `apply_discounts`. Old library modifies `df`; new library does nothing to `df` and raises no error.
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
