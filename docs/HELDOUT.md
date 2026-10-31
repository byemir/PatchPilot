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
