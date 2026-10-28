# p3-spark-two-attempts

Result file `bench_20261028-102955_muse-spark-1.3.json`, case `p3_groupby_report`, run 2.

## Attempt 1: rejected at visible check
Model diagnosis: pandas 3.0 changed groupby defaults: observed now defaults to True (dropping unobserved categorical groups) and apply now defaults to include_groups=False (so part.shape[1] is 1 not 2).

## Attempt 2: accepted
Model diagnosis: groupby now defaults to observed=True (dropping unobserved categories) and apply excludes grouping columns (width 2->1); avoiding apply and forcing observed=False restores golden output.
