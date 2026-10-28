# n7-spark-two-attempts

Result file `bench_20261028-180119_muse-spark-1.3.json`, case `n7_float32_scalars`, run 4.

## Attempt 1: rejected at visible check
Model diagnosis: NumPy 2 (NEP 50) changed float32-scalar * Python-float promotion from float32 to float64, so x and the float32 accumulation changed value and the `x > bonus` count flipped.

## Attempt 2: accepted
Model diagnosis: NumPy 2 NEP50 keeps float32 scalar * Python float as float32 and keeps float32 total, while NumPy 1 promoted to float64; forcing the multiply and accumulation in Python float reproduces the old float64 behavior on both versions.
