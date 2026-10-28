# n6-wonder-first-try

Result file `bench_20261028-174452_muse-wonder-1.0.json`, case `n6_uint8_scaling`, run 1.

## Attempt 1: accepted
Model diagnosis: NumPy 2's NEP 50 weak promotion keeps a uint8 scalar multiplied by a Python int in uint8, wrapping overflow modulo 256, whereas NumPy 1 promoted the result. Widening pixels to int64 before arithmetic prevents overflow on both versions.
