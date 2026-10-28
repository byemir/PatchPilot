# n6-glimmer-local-first-try

Result file `bench_20261028-210347_muse-glimmer_local.json`, case `n6_uint8_scaling`, run 1.

## Attempt 1: accepted
Model diagnosis: Iterating over a uint8 NumPy array yields NumPy uint8 scalars. In NumPy 2.x, `p * gain` is performed with NumPy ufunc semantics and wraps modulo 256, so the accumulated sum is reduced modulo 256. Casting each scalar to Python int before multiplication forces Python big-int arithmetic and removes the overflow.
