# PatchPilot

Finds Python functions that silently return different results after a library upgrade (pandas 2.3 to 3.0, NumPy 1.26 to 2.x), repairs them with a Meta model, and writes a patch only if three gates agree. A local browser app runs the whole thing; the model can be the open-weight Muse Glimmer on your own machine.

![PatchPilot app after a repair run on the 15-function shop set](docs/img/app-done.png)

Meta Global AI Developer Hackathon (Oct 26 to Nov 4, 2026). Track: Indie Developer. Problem statement: Push the Frontier (software). Solo entry. The repository was created on 2026-10-27 (first commit after the kickoff) and holds only work from the event. License: PolyForm Strict 1.0.0 (`LICENSE`), public repository; the organizers confirmed that this meets the rules.

## The problem and the idea

After a dependency upgrade some code keeps passing its tests and quietly returns different numbers: pandas 3 makes datetime-to-integer conversions 1000 times smaller, NumPy 2 turns the string "0" into True, a chained assignment stops writing. PatchPilot lists such functions (`scan`), has a model propose a patch, and accepts it only if it passes three gates:

1. **Visible check:** the recorded inputs reproduce the output of the old library.
2. **Hidden check:** held-out inputs the model never sees.
3. **Differential check:** generated inputs run through the original code on the old library and the patched code on both libraries.

Your files change only when you press **Apply** (or pass `--apply`); **Undo** restores the original. PatchPilot's own code uses only the Python standard library.

## Meta models used

| model | how it is used | where it runs |
|---|---|---|
| Muse Glimmer 30B (open weights, Apache 2.0), Q4_K_M GGUF | the repair loop, served with llama.cpp; no API key, requests go only to a loopback address | one Apple M2 Ultra Mac |
| Muse Spark 1.3 | hosted, Meta Model API (Chat Completions): same gates, same benchmark | Meta |
| Muse Wonder 1.0 | hosted, Meta Model API (Chat Completions): same gates, same benchmark | Meta |
| Muse Spark Open (`meta-models/muse-spark-open-1026`, open weights) | hosted on Baseten's inference service (Chat Completions): same gates, same benchmark | Baseten |
| Muse Spark Open (`accounts/fireworks/models/muse-spark-open`, open weights) | the same model hosted on Fireworks (Chat Completions): shop set run once | Fireworks |

Every model the repair loop calls is a Meta model. Glimmer weights: `meta-models/Muse-Glimmer-30B-GGUF`, revision `b44f1072cf75e918a1b82a3a17b45c4389b076e7`, file `Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf` (sha256 `4cc57c0f51040a226e5a72cc47b7613f7772950e460a665f7083de89f183f60e`); llama.cpp 0.8.0 (build 11960). Hardware, hashes and the exact commands: `docs/DETAILS.md`, "How the local model is run".

## Try it

Needs Python 3.12 and internet for the first step (a few minutes).

**1. Build the four pinned library environments (once):**

    PYTHON312=/path/to/python3.12 ./scripts/setup_envs.sh

(The app shows "The pinned library environments are missing" until this has been run.)

If `python3.12` is not on your PATH (Python 3.13 or newer will not work: the pinned NumPy 1.26.4 has no wheel for it), install one, for example `conda create -n py312 python=3.12` or `brew install python@3.12`, and pass its full path as `PYTHON312`.

**2. Check, no model and no key:**

    python -m patchpilot.app --root examples

Open `127.0.0.1:8765`, pick `shop/scan.json`, press **Check**: of 15 functions we wrote, 5 are unaffected, 3 fail loudly, 7 differ silently.

**3. Offline tests (no model, no key; twenty tests, about five minutes):**

    bash scripts/run_offline_tests.sh

**4. Repair with the open-weight model on your own machine:**

    brew install llama.cpp
    hf download meta-models/Muse-Glimmer-30B-GGUF --local-dir ~/models/muse-glimmer --include "Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf"
    llama-server -m ~/models/muse-glimmer/Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf -a muse-glimmer -ngl 99 -c 65536 -np 1 --host 127.0.0.1 --port 8080 --chat-template-kwargs '{"reasoning_strength":"low"}'

Then press **Repair** in the app, or run `bash scripts/demo_repair.sh` (one function, one command, your file untouched). **Hosted models:** put a Meta Model API key in the key file described in `docs/DETAILS.md` ("Run the agent") and the app offers Muse Spark and Muse Wonder; a Baseten key in `~/.config/patchpilot/baseten_key` adds Muse Spark Open, a Fireworks key in `~/.config/patchpilot/fireworks_key` adds the same model on Fireworks. Each key is sent only to its own service.

**Your own code:** `python -m patchpilot.repair my_module.py my_function --inputs probes.json --lib pandas --endpoint http://127.0.0.1:8080/v1`. `python -m patchpilot.capture` records inputs from your own tests. To find which functions of a folder are worth checking first: `python -m patchpilot.discover SRC_DIR --manifest scan.json --probes-dir probes` lists the functions that contain a pandas-3 pattern and have the shape PatchPilot can run, counts the sites it cannot check (methods, notebooks, module-level code), and writes a draft manifest whose input files are placeholders (it only parses the code). Its patterns are a short list and miss real breaks (on our shop example it lists 4 of the 7 silent functions), so `python -m patchpilot.suggest SRC_DIR` can ask a model about the remaining functions; its answers are hypotheses to test with real inputs, not findings. Fill them from your own tests with `capture`, or let a model propose them: `python -m patchpilot.propose scan.json --endpoint http://127.0.0.1:8080/v1` sends the source of each function to the model (local with `--endpoint`, otherwise the hosted model you choose), keeps only inputs that run on the old library, and leaves the verdict to the old-versus-new run; `healthy` then means no difference on those inputs only. Functions must be pure, deterministic, with JSON or small DataFrame (`$df`, `$series`) inputs; a function may live in a project folder (`"root"` in the manifest, with its own interpreters via `"old"` and `"new"`).

No-run alternative: read `docs/RESULTS.md` and `examples/` (recorded patches with the gate outcome per attempt).

## What the runs show

All runs are small samples on code we wrote (17 benchmark cases, the shop set, the ledger project, a frames module, a project package); token counts only, no dollar cost.

| what | result |
|---|---|
| Shop set (15 functions, 7 silent breaks), app, local Glimmer, 3 runs | 6, 7 and 7 repaired; failures stopped by the gates (`examples/shop_result*/`) |
| Ledger project (22 functions, inputs recorded from its own tests) | local Glimmer and hosted Spark: 7 of 7 repaired on the first attempt (`docs/APP_RUNS.md`) |
| DataFrame module (6 functions) | local Glimmer: 3 of 3 repaired in both runs, one wrong patch blocked in run 2 |
| Benchmark, hosted Spark and Wonder, five cases | 125 of 125 runs solved; on the hardest case (p4): Spark 0 of 5, Wonder 3 of 5 |
| Muse Spark Open (open weights, via Baseten): shop set and five benchmark cases | shop: 7 of 7 repaired, all on the first attempt (9,557 tokens, 76 s; `examples/shop_result_spark_open/`). Benchmark, 5 runs per case: 21 of 25 solved, 19 on the first attempt, 84,581 tokens; case n7 only 1 of 5 (`docs/APP_RUNS.md`). One batch, not a rate. Same model on Fireworks, shop set once: 7 of 7 on the first attempt (9,761 tokens, 229 s; `examples/shop_result_spark_open_fireworks/`) |
| Folder to patches on the shop example (`discover`, `propose`, `scan`; Muse Spark Open via Baseten; one run) | `discover` listed 4 of the 7 silent functions and none of the healthy ones; the model proposed inputs for 3 of them in the first run (the fourth in a second run); all four then classified silent; repair: 3 of 4 on the first attempt (10.5, 6.6 and 14.1 s); `clean_names` was not repaired: the diagnosis was right, and the gates rejected all three patches (two at the hidden tests, one at the visible tests). 25,669 tokens in all (inputs 7,975, repair 17,694). One run, code we wrote, not a rate (`examples/chain_result_spark_open/`) |
| NumPy functions: `suggest`, `propose`, `scan` (Muse Spark Open via Baseten; three suggest runs, two chain runs) | `suggest` named 4, 5 and 5 of the 6 shop functions that change under NumPy 2 and that `discover` does not list, and none of the 5 that do not change (`area_under` was never named); 8,628 to 9,469 tokens per suggest run. With model-proposed inputs the second chain run classified 3 functions silent and 2 loud and repaired all 3 silent ones on the first attempt (7,018 tokens, 16.6 s); the 2 loud ones are only reported. In the first chain run `discounted_price` got inputs that did not separate the libraries and was called healthy; in the second run it was silent (1 of 4 inputs). Model output varies between runs. Code we wrote, patterns tuned after a first miss, not a rate (`examples/chain_numpy_spark_open/`) |
| Benchmark, local Glimmer, six cases (low reasoning) | 19 of 30 solved; on cases where a half-fix passes the visible tests (q1 to q3): 42 of 45 (the count of 27 attempts rejected by the hidden check comes from local run files that are not in the repository) |
| Two real third-party projects, one function each (`docs/REAL_PROJECT.md`) | indsl (known break, before its maintainers' fix): Check silent, local Glimmer repaired it in two runs (first attempt, 13,501 tokens, 194 s; second run: second attempt after the visible tests rejected the first patch, 27,052 tokens, 363 s). polyaxon/traceml (flagged by our static count, not known beforehand): Check silent on 2 of 2 inputs (missing values filled with the mean on pandas 2.3, left as NaN on 3.0), local Glimmer repaired it on the first attempt (4,019 tokens, 55 s). All three gates passed on every accepted patch. The traceml finding was reported upstream (https://github.com/polyaxon/traceml/issues/33; no reply yet). The projects' own tests we ran (8 and 7 tests) pass with and without the patch on both pandas versions, so they did not catch the break. One function per project, our inputs, not a rate |

Impact: `docs/IMPACT.md`; a static count of three pandas-3 patterns in 16 libraries and 7 teaching repositories (0 real hits in the libraries, 5 in teaching notebooks; patterns, not broken programs): `docs/CENSUS.md`. CI gate without a model: `python -m patchpilot.scan scan.json --triage-only --fail-on-silent` exits 1 while a listed function changes silently.

## Limits

- Pure functions with JSON or small-table inputs, one library pair per manifest; you list the functions (`discover` suggests candidates; `capture` or `propose` help with inputs). Python on macOS or Linux, not Windows. Results are compared by values, column names and index, not dtype.
- Model code runs on your machine with your user's privileges, inside an OS-level sandbox (macOS `sandbox-exec`, Linux Landlock); this is not a hardened security boundary. The Linux layer was tested on one cloud VM without a model run.
- All model runs were made on one Apple M2 Ultra Mac. Not tested: Windows, whole real repositories, other quantizations or models, hosted-call cost.
- The Retry button for a failed row was tested with scripted replies only; per-row Repair was run once with the local model.
- Accepted means the patch passed the three gates; read the diff before using it.

## Third-party software

PatchPilot's own code imports only the standard library (optional exception: `patchpilot/ui_smoke.py` imports Playwright if installed). pandas and NumPy (BSD 3-Clause) and pytest are installed from PyPI into the pinned environments, only as the libraries under repair. llama.cpp (MIT) serves the local model. Muse Glimmer is Apache 2.0; Muse Spark and Muse Wonder are used under Meta's API terms. No third-party source code is in the repository.

## More

`docs/DETAILS.md` (full setup, isolation tests, every result table, per-case numbers), `docs/RESULTS.md`, `docs/CASES.md`, `docs/IMPACT.md`, `docs/engineering-log.md`, `docs/training-notes.jsonl`.
