# Held-out run of the chain on eight projects (2026-10-31)

Why: our patterns and prompts were tuned on the shop example and on indsl, so those results are not an independent test. The list, the procedure and what would be reported were written before any repository was cloned (`docs/census/PREREGISTERED4.txt`, commit 4822059). One run per repository: `discover --limit 10`, `propose` and `scan` with Muse Spark Open (Baseten), effort low, in the pinned pandas 2.3.3 and 3.0.6 environments (pandas and NumPy only).

Tooling bug found in the first attempt: `scripts/heldout.sh` called `timeout`, which macOS does not have, so no repository was cloned and nothing was run. Fixed in commit 3ad66d0 (Python timeout); the run below is the first real run.

| repository | commit | candidates | sites skipped | got inputs | healthy | silent | loud | invalid |
|---|---|---|---|---|---|---|---|---|
| abu | 8a48f0c | 2 | 14 | 0 | 0 | 0 | 0 | 2 |
| modin | 7ca200b | 0 | 4 | 0 | 0 | 0 | 0 | 0 |
| pytimetk | 246299c | 1 | 2 | 0 | 0 | 0 | 0 | 1 |
| pygraphistry | 968066c | 6 | 2 | 0 | 0 | 0 | 0 | 6 |
| siuba | 815f55b | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| hamilton | 9371d64 | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| pandera | 1850590 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| django-rest-pandas | 7bdf912 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| total | | 11 | 25 | 0 | 0 | 0 | 0 | 11 |

Result: `discover` listed 11 functions of the right shape in 4 of the 8 projects (the other 4 had pattern sites only in methods, notebooks, scripts or module-level code, which PatchPilot cannot run). None of the 11 could be classified: for every one, the model's inputs raised `ModuleNotFoundError` on the old library, because the function needs a library that is not in the pinned environments (matplotlib for 2 abu functions, polars for 1 pytimetk function, typing_extensions for 6 pygraphistry functions, the project itself and scikit-learn for 2 hamilton functions). Two replies per function, 42,533 tokens in all for `propose`; `scan` made no repair call.

What this shows: on code we had not tuned on, the limit is not the model or the gates but the environment. A function that imports a library outside the pinned environments cannot be run, so it cannot be classified, and we report it as invalid. What it does not show: whether these 11 functions break on pandas 3; nothing was run on them. Eight projects, chosen because they had a pattern site, so not a sample of all projects.

How to run such a project: give the target its own `old` and `new` interpreters (`"old"` and `"new"` keys in the manifest; used for indsl and traceml, `docs/REAL_PROJECT.md`). Building those environments per project is manual work that this run deliberately did not do.

## Exploratory follow-up, not pre-registered: pygraphistry with its own environment

Written after the pre-registered result above was known, so it is not part of the table. The six pygraphistry candidates had failed only because libraries were missing. We built one environment per side from the project's own dependencies (`pip install` of the cloned project, then pandas 2.3.3 or 3.0.6 with NumPy 2.5.4), gave the six targets `old` and `new` interpreters, and ran `propose` and `scan` once with the same model and effort. Two more things were needed, both found in this run:

1. The runner copies the project folder into the sandbox and left out every file above 200 KB; `graphistry/compute/gfql/row/pipeline.py` is 307 KB, so the import failed with `ModuleNotFoundError`. The limits can now be raised for one run with `PATCHPILOT_MAX_FILE` and `PATCHPILOT_MAX_TREE` (defaults unchanged, caps 2 MB and 100 MB; tests in `runner_test`). This run used 400,000 and 60,000,000 bytes.
2. Nothing else in the tool, the prompts or the gates was changed.

| function | inputs | class on the model's inputs |
|---|---|---|
| `graphistry/compute/gfql/search_any.py:_has_string_content` | 4 | healthy (same output on all 4) |
| `graphistry/feature_utils.py:check_if_textual_column` | 4 | healthy (same output on all 4) |
| `graphistry/compute/predicates/str.py:_pandas_handle_na` | 4 | loud: raises TypeError on pandas 3 for 1 of 4 inputs |
| `graphistry/compute/gfql/datetime_search_index.py:_zone_codes` | none | invalid: the model's inputs raised on the old library (a module-level cache registered twice, then a `None` argument) |
| `graphistry/compute/gfql/row/ordering.py:_native_epoch_ticks` | none | invalid: the model gave strings where the function needs integers, then `None` |
| `graphistry/compute/gfql/wysiwyg.py:_tz_abbrev_by_offset` | none | invalid: the model gave inputs without a datetime column, then `None` |

20,211 tokens for `propose`; no function was silent, so `scan` made no repair call. Raw files: `docs/census/heldout_20261031/exploratory_pygraphistry/`.

What it shows: with the environment and the size limit solved, 3 of the 6 candidates could be run and classified, none silently different on these inputs. What it does not show: that the three invalid functions are safe (nothing was run on them), that `healthy` means safe (four model-written inputs each), or that the `loud` result is a real defect: it raises for 1 of 4 inputs and we have not read why. One project, one run.
