# n8-glimmer-local-differential-rejection

Result file `bench_20261029-052806_muse-glimmer_local.json`, case `n8_string_to_bool`, run 1.

## Attempt 1: rejected at differential
Model diagnosis: numpy 2 changed how astype(bool) converts a string array, so non-empty strings like "0" are now treated differently from numpy 1.26. The logic should be based on the flag value "0" vs non-zero instead of relying on NumPy bool casting.
Counterexample returned to the model: input {"flags": ["0", "00"]}; expected {"count": 0, "enabled": [false, false]}; got {"count": 1, "enabled": [false, true]} (patched@new)

## Attempt 2: accepted
Model diagnosis: np.array(flags).astype(bool) changed semantics in NumPy 2.x; string arrays are now always truthy, so "0" and "00" are treated as True. The intended logic is numeric zero vs non-zero, so the bool conversion must be based on the integer value of each flag string.
