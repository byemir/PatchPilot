# p4-wonder-differential-recovery-before-layer

Result file `bench_20261027-191341_muse-wonder-1.0.json`, case `p4_label_histogram`, run 3.

## Attempt 1: rejected at visible check
Model diagnosis: pandas 3 astype(str) preserves missing values under the new string dtype (instead of stringifying None to 'None'), so value_counts(dropna=True) drops those rows; pandas 3 value_counts(sort=False) also no longer returns the old groupby lexicographically-sorted key order. Explicitly stringifying missing sentinels and sorting keys restores pandas 2 behavior on both versions.

## Attempt 2: rejected at differential
Model diagnosis: Pandas 3 infers a string dtype that converts None to NaN and astype(str) leaves it missing, so value_counts drops it; value_counts(sort=False) also now returns appearance order instead of the old sorted group order.
Counterexample returned to the model: input [[], ["t1", "a"]]; expected [["t1", "a", 1]]; got {"error": "ValueError"} (patched@new)

## Attempt 3: accepted
Model diagnosis: pandas 3 infers a NaN-sentinel string dtype and preserves missing values through astype(str), so labels formerly stringified to "None"/"nan" are dropped by value_counts, and DataFrame.value_counts(sort=False) no longer returns keys in sorted order. Forcing object dtype preserves the original Python None/"" distinction, explicitly stringifying restores the old labels, and sorting the counted index ...
