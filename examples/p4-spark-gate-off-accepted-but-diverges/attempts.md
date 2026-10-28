# p4-spark-gate-off-accepted-but-diverges

Result file `bench_20261027-204730_muse-spark-1.3.json`, case `p4_label_histogram`, run 2.

## Attempt 1: rejected at hidden check
Model diagnosis: In pandas 3 string columns use NA-preserving str dtype, so astype(str) leaves None/NaN as NA (dropped by value_counts) instead of 'None', and value_counts(sort=False) now preserves appearance order instead of sorted key order.

## Attempt 2: accepted
Model diagnosis: In pandas 3 astype(str) preserves missing values (NA) instead of stringifying them to 'None'/'nan', so those rows are dropped by value_counts, and value_counts(sort=False) now returns occurrence order instead of sorted order.
