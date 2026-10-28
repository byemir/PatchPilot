# p4-wonder-one-shot-first-try

Result file `bench_20261027-225746_muse-wonder-1.0.json`, case `p4_label_histogram`, run 3.

## Attempt 1: accepted
Model diagnosis: pandas 3 preserves missing values through astype(str) using the new string dtype (so None/''-derived NaN rows are dropped by value_counts) and DataFrame.value_counts(sort=False) now returns first-appearance rather than sorted-index order; the fix forces object dtype and Python str() conversion to preserve 'None'/'nan' strings, and explicitly sorts the counts by (team, label).
