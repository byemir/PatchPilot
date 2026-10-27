# PatchPilot
Autonomous agent that repairs Python projects broken by dependency upgrades, focusing on silent behavior changes. Built during the Meta Global AI Developer Hackathon (Oct 26 - Nov 4, 2026).

## Benchmark cases

All cases are **synthetic**: small programs written for this project and derived from library release notes and from running both versions. They are not taken from real open-source projects. Each case keeps its recorded inputs (`inputs.json`, `golden.json`), held-out inputs that are never shown to the model (`hidden_inputs.json`, `hidden_golden.json`), a `known_good.json` patch and `known_bad/` patches. Golden outputs come from the OLD library version.

| case | library change (old -> new) | what silently changes |
|---|---|---|
| p1_epoch_seconds | pandas 2.3.3 -> 3.0.6 | datetime unit ns -> us, `astype("int64")` is 1000x smaller |
| p2_dst_day_offset | pandas 2.3.3 -> 3.0.6 | `Timestamp + Day(n)` across DST: 24 h becomes a calendar day |
| p3_groupby_report | pandas 2.3.3 -> 3.0.6 | categorical `groupby` drops empty categories; `apply` loses the grouping column |
| p4_label_histogram | pandas 2.3.3 -> 3.0.6 | `astype(str)` keeps None/NaN as NaN; `DataFrame.value_counts(sort=False)` order |
| n6_uint8_scaling | NumPy 1.26.4 -> 2.5.4 | uint8 scalar arithmetic wraps around |
| n7_float32_scalars | NumPy 1.26.4 -> 2.5.4 | float32 scalar * Python float stays float32 (sum digits, comparisons) |

A case is counted only if `python -m patchpilot.validate_case benchmarks/<case>` reports it valid (old OK, new silently broken, tests green on both, hidden inputs break too, known-good patch accepted, known-bad patches rejected).

