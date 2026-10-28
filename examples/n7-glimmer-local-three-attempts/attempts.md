# n7-glimmer-local-three-attempts

Result file `bench_20261028-210626_muse-glimmer_local.json`, case `n7_float32_scalars`, run 2.

## Attempt 1: rejected at visible check
Model diagnosis: Iterating over a float32 NumPy array in a Python loop makes the scalar multiplication and the in-loop float32 accumulation depend on NumPy’s scalar promotion rules which changed in NumPy 2. The mixed Python/NumPy arithmetic causes tiny rounding differences in the total and, for the second probe, pushes the `x > bonus` comparison below the threshold so hits become zero. Using fully vectorised float...

## Attempt 2: rejected at visible check
Model diagnosis: The multiplication and comparison are now performed with NumPy 2’s stricter up-casting, so `v * rate` is evaluated in float64 and the `>` test against `bonus` changes the hit count and the float32 accumulation drifts. Forcing the whole computation to stay in float32, including casting `rate` and `bonus` to float32 before the loop, reproduces the NumPy 1.26 rounding and comparison behaviour on both...

## Attempt 3: accepted
Model diagnosis: The loop mixes NumPy float32 scalars with Python floats; NumPy 2 changed promotion and scalar behaviour so `v * rate` and the `>` comparison are evaluated with different precision, causing both the accumulated total and the hit count to diverge. Converting the array to native Python floats before arithmetic makes the computation deterministic across NumPy versions.
