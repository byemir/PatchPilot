# PatchPilot
Agent that proposes and verifies patches for Python code that broke silently after a dependency upgrade: the tests stay green, the output is wrong. Built during the Meta Global AI Developer Hackathon (Oct 26 - Nov 4, 2026); the first commit of this repository is from Oct 27.

**At a glance**

- A patch is accepted only if it passes three gates: the visible tests, hidden tests the model never sees, and a differential check against the old library.
- Twelve cases (pandas 2.3 to 3.0, NumPy 1.26 to 2.x): eleven synthetic ones derived from documented library changes and one (p7) built around a function copied from the open-source project scikit-FIBERS; not tried on whole real repositories. Two further cases come from third-party repositories (indsl and Kythera, each in two variants) and are reported separately under "Cases from third-party code".
- Hosted Muse Spark and Muse Wonder solved 125 of 125 runs on five cases; on the hardest one (p4), Spark 0 of 5 and Wonder 3 of 5. Muse Glimmer running locally solved 19 of 30 runs on six cases (low reasoning).
- All runs were made on one Apple M2 Ultra Mac; no other platform was tested.
- Why it matters and what it does not show: [`docs/IMPACT.md`](docs/IMPACT.md). One command from a function to a gated patch: `python -m patchpilot.repair` (see "Try it on your own function").

## Models and where they run

| model | how it is used | where it runs |
|---|---|---|
| muse-spark-1.3 | hosted, Meta Model API (Chat Completions) | Meta |
| muse-wonder-1.0 | hosted, Meta Model API (Chat Completions) | Meta |
| Muse Glimmer 30B (open weights, Apache 2.0), Q4_K_M GGUF | served locally with llama.cpp (Metal); `--endpoint http://127.0.0.1:8080/v1`; no API key is read or sent and requests only go to a loopback address | the Apple M2 Ultra Mac used for development |

The same gates and the same benchmark runner are used for all three models. The local weights are `meta-models/Muse-Glimmer-30B-GGUF`, file `Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf`, 16756683904 bytes, sha256 `4cc57c0f51040a226e5a72cc47b7613f7772950e460a665f7083de89f183f60e`; llama.cpp 0.8.0 (build 11960, commit 8642541b2). The result files record the server build and the model file name. The commands below follow the Muse Glimmer documentation and were run on this machine only:

    brew install llama.cpp
    hf download meta-models/Muse-Glimmer-30B-GGUF --local-dir ~/models/muse-glimmer --include "Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf"
    llama-server -m ~/models/muse-glimmer/Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf -a muse-glimmer -ngl 99 -c 65536 -np 1 --host 127.0.0.1 --port 8080 --chat-template-kwargs '{"reasoning_strength":"low"}'
    python -m patchpilot.bench --endpoint http://127.0.0.1:8080/v1 --cases n6_uint8_scaling --effort low --repeats 5 --score-seed 1

## How it works
For each case the agent receives the program source, the golden output (from the old library) and the actual output on the new library, and proposes a patch. By default this is one model call per attempt with a JSON reply and no tool use; `--tools` mode (see below) adds a tool conversation per attempt. A rejected attempt returns feedback to the model. A patch is accepted only if all three gates pass:

1. **Visible check:** the recorded inputs reproduce the golden output (generated with the OLD library).
2. **Hidden check:** held-out inputs that are never shown to the model.
3. **Differential check:** generated inputs run through the original code on the old library and the patched code on both libraries; core divergences reject the patch.

Defaults: up to 3 attempts per run, 60000 token budget (checked before each model call, so a run can exceed it by one call). The benchmark runner can switch the differential gate off (`--no-differential`) and score accepted patches with it afterwards at another seed (`--score-seed`).

## Isolation of model code

Patched code runs in a subprocess inside a temporary copy of the case (`patchpilot/sandbox.py`) with a wall-clock timeout (the process group is killed), a CPU-time limit and a minimal environment without inherited secrets. Model code runs on your machine with your user's privileges; this runner is not a hardened security boundary. On macOS, `bench` and `agent` additionally wrap model code in `sandbox-exec` (no read or write access to the home directory and the repository except the sandbox environments, no network), re-exec themselves with a minimal environment, read the API key from a file instead of the environment, and refuse to run model code if the harness environment holds secret-looking variables or the isolation self-test fails. Shown on one macOS machine with fake secrets (`patchpilot/isolation_test.py`, `patchpilot/negative_test.py`, details in the engineering log): a fake secret file under `~/.config`, the repository's `hidden_golden.json` (absolute path), a home directory listing and a loopback connection were blocked. Reading the harness's initial environment through `sysctl` was NOT blocked by the profile, which is why the environment must not hold secrets. Not tested: memory inspection tools (`lldb`, `vmmap`, `gcore`), other same-user processes that hold secrets, Linux, external network. On other platforms `bench` and `agent` are written to refuse to run unless `--no-fs-deny` is given (only the missing `sandbox-exec` case was tested); such runs are marked `fs_deny=false` and are not counted. There is no memory limit. With the key file present, `bench` and `agent` refuse `--no-fs-deny` (checked once each; the check lives in the argument handling).

## Without running anything

The numbers and patches behind the results can be read without running the benchmark:

- [`docs/RESULTS.md`](docs/RESULTS.md): one row per case and result file in `results/`, generated by `scripts/make_showcase.py`. It lists every file, including the 1-run smoke tests.
- [`examples/`](examples/): twelve patches written by the models in recorded runs, chosen to show the cases and the gates (not a random sample). Each has the gate outcome per attempt and the model's own diagnosis; where the differential rejected an attempt, the counterexample that was returned to the model. One example is a patch that was accepted with the differential gate off and failed the differential afterwards. "Accepted" means the patch passed the gates that were on in that run; no review beyond the gates is claimed.
- [`docs/engineering-log.md`](docs/engineering-log.md) and [`docs/training-notes.jsonl`](docs/training-notes.jsonl): what was measured, what failed and what was not tested.

## Platform

All recorded runs were made on one Apple Silicon Mac (Apple M2 Ultra, macOS 26.6.2); no other platform was tested. The isolation layer uses `sandbox-exec`, which exists only on macOS.

## Setup
Requires Python 3.12 (tested with 3.12.16). `PYTHON312` must point to a Python 3.12 interpreter; on the macOS machine used for development `python3.12` was not on `PATH`, so the path was passed explicitly. A fresh clone with this script built the four environments and reported all six cases valid (six cases at that time; p5, p6 and n8 were added later and validated in the same environments). One command builds four pinned virtual environments under `.sandboxes/` and validates all cases:

    PYTHON312=/path/to/python3.12 ./scripts/setup_envs.sh

A case is valid only if the old library is OK, the new one silently breaks, tests are green on both, hidden inputs break too, the known-good patch is accepted and the known-bad patches are rejected. Validation of a single case:

    python -m patchpilot.validate_case benchmarks/p1_epoch_seconds

## Run the agent
The runner (`patchpilot/*.py`) imports only the Python standard library, including `urllib` for the model API; pandas and NumPy are needed only inside the four sandbox environments.

    # one-time, from your own terminal: the key is typed hidden and goes only into this file
    ( umask 077; mkdir -p ~/.config/patchpilot && chmod 700 ~/.config/patchpilot; printf 'Meta API key: '; stty -echo; read -r K; stty echo; echo; printf '%s\n' "$K" > ~/.config/patchpilot/meta_key; chmod 600 ~/.config/patchpilot/meta_key; unset K )
    python -m patchpilot.meta_client keycheck   # prints the file mode and the key length, never the key
    python -m patchpilot.agent benchmarks/p1_epoch_seconds .sandboxes/pd23/bin/python .sandboxes/pd30/bin/python

Cases n6/n7 use `.sandboxes/np126` and `.sandboxes/np2`. Benchmark runner: `python -m patchpilot.bench --help`.

## Try it on your own function

`patchpilot.make_case` builds a case folder from one function in one file. You give it the file, the function name, a JSON list of keyword-argument inputs, and two interpreters (old and new library version):

```
python -m patchpilot.make_case --src my_module.py --fn my_function --inputs probes.json \
    --old /path/to/old/python --new /path/to/new/python --lib pandas --out my_case
python -m patchpilot.agent my_case /path/to/old/python /path/to/new/python --lib pandas
```

The same two steps as one command, `patchpilot.repair`: it builds the case in a temporary folder, repairs it behind the three gates, writes the accepted patch as a diff plus a JSON report, and changes your file only with `--apply` (and only if the file is unchanged since the case was built):

```
python -m patchpilot.repair my_module.py my_function --inputs probes.json --lib pandas \
    --endpoint http://127.0.0.1:8080/v1 [--apply]
```

Default interpreters are `.sandboxes/pd23` and `.sandboxes/pd30` for pandas, `np126` and `np2` for numpy (override with `--old` and `--new`). Exit code 0 means a patch passed the gates, 1 means none did, 2 means the case could not be built. "Accepted" means it passed the gates that were on; read the diff before you use it. On `examples/own_function/censor_adapter.py` with the local Glimmer server one run was accepted on the first attempt (2230 tokens, 38 s for the repair, 43 s for the whole command on our Mac); that is one run, not a rate. `python -m patchpilot.repair_test` checks the command offline with a scripted model reply (accepted, rejected, unknown function, `--apply`, changed file).

The golden output comes from the old interpreter. Held-out inputs are derived with the differential generator and kept only if the old library reproduces them (or pass `--hidden-inputs`). It stops with a reason if the function raises on the old library, is not deterministic, crashes on the new library (a loud failure) or gives the same output there (nothing to repair).

Limits: the function must live in one self-contained file (standard library plus the library under repair), take JSON-friendly arguments and return JSON-friendly values (otherwise write a small adapter in the same file), and be deterministic. No known-good or known-bad patches are generated. `python -m patchpilot.make_case_test` checks the builder offline on three existing functions.

Example in `examples/own_function/`: the unmodified `censor` function from scikit-FIBERS (see `docs/THIRD_PARTY_NOTICES.md`) plus a thin adapter. One run with muse-spark-1.3 solved it on the first attempt (2696 tokens), and one run on the `n8` function rebuilt this way solved it on the first attempt (3350 tokens). These are single runs, not a success rate. `censor` is also the source of p7, so the breakage pattern is not new; what is new is that the case was generated from the original code by one command. Muse Glimmer on the same case (local, effort low, `bash scripts/demo_own_function.sh`) solved it in 6 runs out of 6, 5 on the first attempt (2167 to 4686 tokens per run; the sixth needed two attempts). These are repeats of one case, not six cases. `bash scripts/run_offline_tests.sh` runs the six offline tests (no model call, no real key; 70 seconds in total on our Mac in the last run: 3, 38, 11, 14, 1 and 3 s).

## Limitations
Eleven of the twelve main cases are synthetic and one (p7) contains code copied from one real open-source project; two further cases (indsl and Kythera, each with a scoped variant) are copied from third-party repositories and are reported separately; PatchPilot has not been tried on whole real repositories. Sample sizes in `results/` are small (1 to 5 runs per case and setting; the first three files have 3 runs per case, one smoke test has 1), so they show direction only. Only token counts were recorded, no dollar cost per run. The first two bench files and earlier runs ran without the differential gate (see the engineering log).
Not tested or not measured: dollar cost and run time of hosted calls (not recorded), Linux and other non-macOS platforms, memory inspection tools (`lldb`, `vmmap`, `gcore`), other same-user processes that hold secrets, external network, real open-source projects, Muse Spark Open and other open-weight models, other quantizations of Muse Glimmer, reasoning levels of Glimmer other than low and medium (medium on four cases only), hosted effort levels other than low (one minimal-effort batch), a tools run with a larger token budget and tools mode with a local endpoint.

Engineering log and technical notes: [`docs/engineering-log.md`](docs/engineering-log.md), [`docs/training-notes.jsonl`](docs/training-notes.jsonl).

## Results so far

All numbers come from the files in `results/`. Cases are synthetic, samples are small, only token counts were recorded. The rows of the first table below were produced before the isolation layer existed: model code ran without the OS layer and the API key was in the process environment (none of the files in that table has an `fs_deny` field). A scan of the 126 saved patches found only imports of pandas, numpy, collections and math, so no sign of file or environment access was found; the scan cannot rule it out.

| setting | model | result | file |
|---|---|---|---|
| effort=minimal, differential gate on, 5 runs per case | muse-spark-1.3 | solved 25/30 runs: n6 5/5, n7 5/5, p1 5/5, p2 5/5, p3 5/5, p4 0/5 | `bench_20261027-185732_muse-spark-1.3.json` |
| p4 only, effort=low, gate on, 5 runs | muse-spark-1.3 | 0/5 | `bench_20261027-190705_muse-spark-1.3.json` |
| p4 only, effort=low, gate on, 5 runs | muse-wonder-1.0 | 1/5 | `bench_20261027-191341_muse-wonder-1.0.json` |
| p4 only, effort=low, gate off, accepted patches scored with the differential at seed 1 | muse-spark-1.3 | 2/5 accepted, 0 pass the differential | `bench_20261027-204730_muse-spark-1.3.json` |
| p4 only, effort=low, gate off, accepted patches scored with the differential at seed 1 | muse-wonder-1.0 | 3/5 accepted, 1 passes the differential | `bench_20261027-205730_muse-wonder-1.0.json` |

Observed in two wonder-1.0 runs (n=2; one before and one after the isolation layer): with the gate on, the differential rejected an attempt that had passed the visible and hidden checks, the counterexample was returned to the model and the next attempt passed. p4 is mostly unsolved; with the gate off, 4 of the 5 accepted patches failed the differential, which is why accepted counts and differential-scored counts are reported separately. Details and caveats: the engineering log.

## Results under the isolation layer: p4

p4_label_histogram only, effort=low, 5 runs per model, differential used as a gate and accepted patches re-scored with the differential at another seed, one invocation per model (the result files have counted=true and fs_deny=true).

| model | solved | first try | accepted patches passing the re-scored differential | avg tokens | file |
|---|---|---|---|---|---|
| muse-spark-1.3 | 0/5 | 0 | 0 | 21230 | `bench_20261027-224719_muse-spark-1.3.json` |
| muse-wonder-1.0 | 3/5 | 1 | 3 of 3 | 13066 | `bench_20261027-225746_muse-wonder-1.0.json` |

First failing gate per attempt: spark-1.3 (15 attempts) visible 7, hidden 6, differential 2; wonder-1.0 (13 attempts) visible 6, hidden 3, differential 1, accepted 3. n=5 per model, one synthetic case; these runs differ from the earlier p4 rows, so this is not a controlled comparison. Only token counts were recorded.

## Results under the isolation layer: the other five cases

effort=low, 5 runs per case in each batch, one-shot protocol (no tools), differential used as a gate, accepted patches re-scored with the differential at another seed; every row has counted=true and fs_deny=true. muse-spark-1.3 was run 4 times with the same command, so all 4 of its batches are listed; muse-wonder-1.0 was run once. The cases are synthetic.

| batch (file in `results/`) | model | runs | solved | first try | re-scored differential pass | avg tokens per run | total tokens |
|---|---|---|---|---|---|---|---|
| `bench_20261028-174452_muse-wonder-1.0.json` | muse-wonder-1.0 | 25 | 25 | 22 | 25 | 2832 | 70797 |
| `bench_20261028-102955_muse-spark-1.3.json` | muse-spark-1.3 | 25 | 25 | 22 | 25 | 3440 | 85994 |
| `bench_20261028-173617_muse-spark-1.3.json` | muse-spark-1.3 | 25 | 25 | 24 | 25 | 3122 | 78048 |
| `bench_20261028-180119_muse-spark-1.3.json` | muse-spark-1.3 | 25 | 25 | 22 | 25 | 3221 | 80536 |
| `bench_20261028-181000_muse-spark-1.3.json` | muse-spark-1.3 | 25 | 25 | 22 | 25 | 3565 | 89137 |

Per case (solved / first try / average tokens per run):

| case | wonder-1.0 | spark-1.3 batch 1 | spark-1.3 batch 2 | spark-1.3 batch 3 | spark-1.3 batch 4 |
|---|---|---|---|---|---|
| n6_uint8_scaling | 5/5 / 5 / 1205 | 5/5 / 5 / 1789 | 5/5 / 5 / 2114 | 5/5 / 5 / 2081 | 5/5 / 5 / 1930 |
| n7_float32_scalars | 5/5 / 5 / 2436 | 5/5 / 5 / 3852 | 5/5 / 5 / 3753 | 5/5 / 3 / 4917 | 5/5 / 4 / 4493 |
| p1_epoch_seconds | 5/5 / 4 / 4660 | 5/5 / 4 / 4365 | 5/5 / 4 / 4179 | 5/5 / 5 / 3436 | 5/5 / 4 / 3984 |
| p2_dst_day_offset | 5/5 / 3 / 3787 | 5/5 / 4 / 4115 | 5/5 / 5 / 2934 | 5/5 / 5 / 3018 | 5/5 / 4 / 5139 |
| p3_groupby_report | 5/5 / 5 / 2071 | 5/5 / 4 / 3078 | 5/5 / 5 / 2629 | 5/5 / 4 / 2655 | 5/5 / 5 / 2281 |

125 of 125 runs were solved and 125 of 125 accepted patches passed the re-scored differential; 13 runs needed more than one attempt. These five cases were solved in every run, unlike p4 (see above). The spark batches differ from each other in first-try counts and token averages, which shows the run-to-run variation at n=5; no comparison between the models is drawn from these rows. Only token counts were recorded.

## How the local model is run

The Glimmer runs in this repository use a model served on the same machine, not a hosted API. The agent is pointed at it with `--endpoint http://127.0.0.1:8080/v1` (the endpoint of every run is stored in its `attempt_N.json` under `endpoint`).

- Hardware: Apple M2 Ultra, 192 GiB RAM, macOS 26.6.2
- Server: llama.cpp `version: 0.8.0 (build 11960, commit 8642541b2)`, AppleClang 21.0.0
- Weights: `Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf`, 16756683904 bytes, sha256 `4cc57c0f51040a226e5a72cc47b7613f7772950e460a665f7083de89f183f60e`
- Source: https://huggingface.co/meta-models/Muse-Glimmer-30B-GGUF, revision `b44f1072cf75e918a1b82a3a17b45c4389b076e7` (recorded in the Hugging Face download metadata next to the file; the hash recorded there equals the sha256 above). The model page lists the license as apache-2.0.
- Client: Python 3.12.16

Start the server:

    llama-server -m ~/models/muse-glimmer/Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf -a muse-glimmer -ngl 99 -c 65536 -np 1 --host 127.0.0.1 --port 8080 --chat-template-kwargs '{"reasoning_strength":"low"}'

Check the file and the server, then run one case:

    shasum -a 256 ~/models/muse-glimmer/Muse-Glimmer-30B-KQuant-17GB-Q4_K_M.gguf
    curl -s http://127.0.0.1:8080/v1/models
    .venv/bin/python -m patchpilot.agent benchmarks/r1f_indsl_time_split .sandboxes/pd23/bin/python .sandboxes/pd30/bin/python --lib pandas --model muse-glimmer --effort low --endpoint http://127.0.0.1:8080/v1

## Results with a local open-weight model (Muse Glimmer)

Muse Glimmer 30B (Q4_K_M, llama.cpp b11960, one Apple M2 Ultra Mac). One-shot protocol, differential used as a gate, accepted patches re-scored at another seed, at most 3 attempts, 5 runs per case in one batch per case; every row has counted=true and fs_deny=true. `reasoning_strength` was low through the chat template, which is not the same mechanism as `reasoning_effort=low` on the hosted API. No API key is used and the API cost is zero (electricity is not counted).

| case | solved | first try | re-scored differential pass | avg tokens per run | rejected attempts: visible / hidden / differential | wall clock of the 5-run batch (from start times) | file |
|---|---|---|---|---|---|---|---|
| n6_uint8_scaling | 5/5 | 5 | 5 | 1187 | 0 / 0 / 0 | about 2 min 39 s | `bench_20261028-210347_muse-glimmer_local.json` |
| n7_float32_scalars | 2/5 | 1 | 2 | 5047 | 11 / 0 / 0 | about 9 min 47 s | `bench_20261028-210626_muse-glimmer_local.json` |
| p1_epoch_seconds | 3/5 | 2 | 3 | 2825 | 3 / 0 / 4 | about 5 min 41 s | `bench_20261028-211613_muse-glimmer_local.json` |
| p2_dst_day_offset | 4/5 | 3 | 4 | 5060 | 4 / 0 / 0 | about 9 min 4 s | `bench_20261028-212154_muse-glimmer_local.json` |
| p3_groupby_report | 5/5 | 4 | 5 | 2755 | 2 / 0 / 0 | about 4 min 56 s | `bench_20261028-213058_muse-glimmer_local.json` |
| p4_label_histogram | 0/5 | 0 | 0 | 6604 | 9 / 6 / 0 | not recorded | `bench_20261028-213554_muse-glimmer_local.json` |

19 of 30 runs were solved, 15 on the first attempt, and 19 accepted patches passed the re-scored differential. Of the 58 attempts, 39 were rejected: 29 at the visible check, 6 at the hidden check and 4 at the differential. The longest completion was 2389 tokens (cap 12000) and 0 replies were empty, so the unsolved runs are gate rejections, not truncation, as far as the recorded attempts show. In the three requests of the server log excerpt that was inspected, generation ran at 24.1 to 26.4 tokens per second. For context: the hosted models solved 125 of 125 runs on the five cases other than p4 and, on p4 (one-shot, isolation layer), spark-1.3 0 of 5 and wonder-1.0 3 of 5; Glimmer solved 19 of 25 on the five cases and 0 of 5 on p4. These are different models with different quantization and reasoning mechanisms, one batch per case: no claim is made about the reasons. Token counts include the reasoning trace; the usage object does not report reasoning tokens separately.

### Glimmer at reasoning strength medium (four cases)

Same server, same protocol and same case files, with `reasoning_strength` set to medium per request (5 runs per case, one batch per case, counted=true, re-scored at seed 1). Low is the table above. Different batches, n=5 per cell: this is not enough to say whether the setting matters. Wall-clock times are not reported for the medium batches because another job ran on the same machine during the first one.

| case | solved low / medium | first try low / medium | avg tokens per run low / medium | medium file |
|---|---|---|---|---|
| n7_float32_scalars | 2/5 / 0/5 | 1 / 0 | 5047 / 12775 | `bench_20261028-222025_muse-glimmer_local.json` |
| p1_epoch_seconds | 3/5 / 4/5 | 2 / 2 | 2825 / 6478 | `bench_20261028-225035_muse-glimmer_local.json` |
| p2_dst_day_offset | 4/5 / 5/5 | 3 / 4 | 5060 / 5202 | `bench_20261028-230556_muse-glimmer_local.json` |
| p4_label_histogram | 0/5 / 0/5 | 0 / 0 | 6604 / 14800 | `bench_20261028-231826_muse-glimmer_local.json` |

On these four cases both settings solved 9 of 20 runs. Unsolved runs ended with "max attempts reached". Why runs differed was not analysed (patches not read).

### Results on p5, p6 and n8 (all three models)

One-shot, effort low (Glimmer: reasoning strength low), 5 runs per cell, re-scored at seed 1. All 45 runs were solved and passed the re-scored differential, so these cases did not separate the models; they add coverage of three documented behavior changes, not difficulty. Token counts only, no dollar cost. Per-run files and sources: `docs/CASES.md`.

| case | muse-spark-1.3 first try / avg tokens | muse-wonder-1.0 first try / avg tokens | muse-glimmer (local) first try / avg tokens |
|---|---|---|---|
| p5_chained_assignment | 5 / 1407 | 5 / 1511 | 4 / 1493 |
| p6_str_dtype_checks | 5 / 2610 | 5 / 2326 | 4 / 2210 |
| n8_string_to_bool | 5 / 2807 | 5 / 2553 | 1 / 2772 |

### Glimmer, more runs at low (p1, p4, n7)

The same 15-run command was started twice by mistake, so each of these three cases has two batches of 15 runs (counted, reasoning strength low, re-scored at seed 1). Both ran on the same single-slot server together with another batch, so wall-clock times are not reported. Every unsolved run ended with "max attempts reached".

| case | batch A: solved / first try / avg tokens | batch B: solved / first try / avg tokens | pooled solved | files (A, B) |
|---|---|---|---|---|
| p1_epoch_seconds | 14/15 / 9 / 2576 | 12/15 / 7 / 2732 | 26/30 | `bench_20261029-094121_muse-glimmer_local.json`, `bench_20261029-100243_muse-glimmer_local.json` |
| n7_float32_scalars | 5/15 / 1 / 5319 | 3/15 / 0 / 5483 | 8/30 | `bench_20261029-101016_muse-glimmer_local.json`, `bench_20261029-103635_muse-glimmer_local.json` |
| p4_label_histogram | 0/15 / 0 / 6656 | 0/15 / 0 / 6429 | 0/30 | `bench_20261029-084225_muse-glimmer_local.json`, `bench_20261029-085922_muse-glimmer_local.json` |

The two identical batches differ by 2 solved runs on p1 and on n7, which shows the run-to-run spread at n=15. The 5-run rows above (p1 3/5, n7 2/5, p4 0/5) and the medium batches (p1 4/5, n7 0/5, p4 0/5) should be read with that spread in mind; no claim is made about the effect of the reasoning strength.

### Results on p7 (a function copied from scikit-FIBERS)

p7_censor_chained_iloc contains the function `censor` copied verbatim from the open-source project scikit-FIBERS (MIT license) at commit 356c6d5, before the project fixed a pandas 3 chained-assignment problem (its issue #19); the wrapper, test, inputs and the patches that grade it were written for this project and the project's own tests were not used (see `docs/THIRD_PARTY_NOTICES.md` and `docs/CASES.md`). One-shot, effort low (Glimmer: reasoning strength low), 5 runs per model, re-scored at seed 1. All 15 runs were solved on the first attempt and passed the re-scored differential, so this case did not separate the models; the model patches were not compared with the project's own fix. Token counts only.

| model | solved | first try | avg tokens per run | file |
|---|---|---|---|---|
| muse-spark-1.3 | 5/5 | 5 | 3378 | `bench_20261029-084833_muse-spark-1.3.json` |
| muse-wonder-1.0 | 5/5 | 5 | 2760 | `bench_20261029-084952_muse-wonder-1.0.json` |
| muse-glimmer (local) | 5/5 | 5 | 2502 | `bench_20261029-085203_muse-glimmer_local.json` |

### Results on p8 and n9 (three silent breaks in one function)

p8_session_report_three_breaks (pandas) and n9_fleet_report_three_breaks (NumPy) each combine three documented changes in one function (see `docs/CASES.md`). One-shot, effort low (Glimmer: reasoning strength low), 5 runs per cell, re-scored at seed 1. All 20 hosted runs were solved on the first attempt and passed the re-scored differential, so combining three breaks did not make these cases harder for the hosted models. Glimmer solved p8 5/5 and n9 3/5. Token counts only. The model patches were not read.

| case | model | solved | first try | avg tokens per run | file |
|---|---|---|---|---|---|
| p8 | muse-spark-1.3 | 5/5 | 5 | 3125 | `bench_20261029-114531_muse-spark-1.3.json` |
| p8 | muse-wonder-1.0 | 5/5 | 5 | 2354 | `bench_20261029-114656_muse-wonder-1.0.json` |
| p8 | muse-glimmer (local) | 5/5 | 5 | 2495 | `bench_20261029-114846_muse-glimmer_local.json` |
| n9 | muse-spark-1.3 | 5/5 | 5 | 3149 | `bench_20261029-115304_muse-spark-1.3.json` |
| n9 | muse-wonder-1.0 | 5/5 | 5 | 2515 | `bench_20261029-115408_muse-wonder-1.0.json` |
| n9 | muse-glimmer (local) | 3/5 | 2 | 5222 | `bench_20261029-115707_muse-glimmer_local.json` |

## Cases from third-party code

Everything above in the case table is a reproduction we wrote, except p7 (scikit-FIBERS). These two cases come from other people's repositories and are reported separately. The selection rules were written and committed before any search (`docs/REAL_CASES_PROTOCOL.md`); the search log, every examined hit and the reason for each rejection are in `docs/real_cases/candidates.md`. 168 distinct hits were collected, 75 passed a mechanical screen and were decided one by one, ten finalists were rejected after reading their code (reasons in `candidates.md`), two were accepted.

| case | upstream | license | function | code taken from | fixed upstream by |
|---|---|---|---|---|---|
| `r1_indsl_time_split` | cognitedata/indsl | Apache-2.0 | `_split_timeseries_into_time_and_value_arrays` | parent fab55f6dfa82 | PR 639, merge 5ec4a2ed4f |
| `r2_kythera_epoch_seconds` | ziagl888/Kythera | MIT | `panel_to_compact` | parent d0ff0159d9ae | PR 229, merge e3181d5aeb |

The function bodies are copied verbatim by script (`scripts/build_real_case.py`); license texts are in `docs/THIRD_PARTY_NOTICES.md`. The JSON adapter, the inputs, the known-good patch and the known-bad patch are ours. Both cases passed `validate_case` before any model saw them. Both are the same documented change (pandas 3.0 datetime resolution inference: conversion to integers gives values 1000x smaller, see `docs/CASES.md` for the quoted release note), so they are two real examples of one mechanism, not two mechanisms. The target was three cases; two were found within the time box.

Two variants were run with Glimmer at low effort on the local server, five runs each. In `r1`/`r2` the adapter sat in the editable file, and the models often rewrote the adapter instead of the third-party function. In `r1f`/`r2f` the adapter is read-only (`tests/adapter.py`), so the repair has to change the third-party function. The unscoped runs are kept as they were (`docs/real_cases/results_unscoped_20261029.json`); the scoped runs are in `docs/real_cases/results_scoped_20261029.json` with every diff.

| variant | runs | passed visible and hidden | first attempt | tokens, all attempts | third-party function changed | differential gate |
|---|---|---|---|---|---|---|
| r1, adapter editable | 5 | 5 | 4 | 2177 to 5251 | 0 of 5 | PASS 5 |
| r2, adapter editable | 5 | 5 | 4 | 2684 to 7581 | 3 of 5 | WEAK 5 |
| r1f, function only | 5 | 5 | 2 | 2199 to 5277 | 5 of 5 | PASS 5 |
| r2f, function only | 5 | 5 | 4 | 2427 to 6504 | 5 of 5 | WEAK 5 |

Reading of the 10 scoped patches (by eye, from the diffs in the results file): all five `r1f` patches compute elapsed seconds from `total_seconds()` and do not depend on the pandas version. In `r2f`, three patches are unit-independent (`pd.Timestamp(0)` difference, `.timestamp()`, forcing `datetime64[ns]`). Two read `pd.__version__` and divide by `10**6` on pandas 3.0 and above; one of them also imports `packaging`. They pass every gate on the recorded inputs, which come from strings and are microsecond data on pandas 3. They are wrong for nanosecond data: on pandas 3.0.6 a `datetime64[ns]` value for 2024-01-01 gives 1704067200000 with `// 10**6`, correct is 1704067200. The differential gate would be the check that catches this, but it returned WEAK on `r2` (fewer than 20 valid generated probes, `MIN_VALID` in `patchpilot/differential.py`), so it did not.

Limits of this section: two cases, one change class, one model, one effort level, five runs each, one machine.

## Tools mode (experimental, p4 only)

`--tools` lets the model call `run_tests` and `run_probe` during an attempt (one conversation per attempt, at most 12 tool calls, and the same 60000-token run budget, which is checked only before each model call and was exceeded in several runs). `run_probe` runs inputs chosen by the model through the original code on the old library and through the candidate on the new library; it is an oracle for the original behavior on those inputs. The gate is unchanged and is not available to the model.

p4_label_histogram, effort=low, 5 runs per model, differential used as a gate, accepted patches re-scored at another seed (result files have counted=true, tools=true, fs_deny=true):

| model | solved | first try | accepted patches passing the re-scored differential | runs ended by the token budget | avg tokens | file |
|---|---|---|---|---|---|---|
| muse-spark-1.3 | 2/5 | 1 | 2 of 2 | 3 | 53834 | `bench_20261028-094310_muse-spark-1.3_tools.json` |
| muse-wonder-1.0 | 2/5 | 1 | 2 of 2 | 3 | 67056 | `bench_20261028-095554_muse-wonder-1.0_tools.json` |

Same setting without tools (table above): spark 0/5 (avg 21230 tokens), wonder 3/5 (avg 13066). First failing gate per attempt, 16 attempts with tools: visible 2, hidden 0, differential 8, invalid reply 2, accepted 4; 28 attempts without tools: visible 13, hidden 9, differential 3, accepted 3. No run with tools reached a third attempt. Two of the four accepted patches were submitted from the last files passed to a tool after the token budget stopped the conversation. With tools, prompt tokens (the context is re-sent on every call) were 61 percent (spark) and 73 percent (wonder) of all tokens. n=5 per model, one synthetic case, runs differ: this pilot gives no evidence that the tools improve the success rate, and with the same budget they used 2.5 to 5.1 times the tokens per run. Only token counts were recorded.


## Benchmark cases

Eleven of the twelve cases are **synthetic**: small programs written for this project and derived from library release notes and from running both versions. p7 is different: the function `censor` is copied verbatim from the open-source project scikit-FIBERS (MIT license, commit 356c6d5, notice in `docs/THIRD_PARTY_NOTICES.md`); the wrapper, tests and inputs that grade it were written for this project. Each case keeps its recorded inputs (`inputs.json`, `golden.json`), held-out inputs that are never shown to the model (`hidden_inputs.json`, `hidden_golden.json`), a `known_good.json` patch and `known_bad/` patches. Golden outputs come from the OLD library version. Two further cases, `r1`/`r1f` (cognitedata/indsl) and `r2`/`r2f` (ziagl888/Kythera), are copied from third-party repositories, are not part of the twelve, and are described under "Cases from third-party code".

| case | library change (old -> new) | what silently changes |
|---|---|---|
| p1_epoch_seconds | pandas 2.3.3 -> 3.0.6 | datetime unit ns -> us, `astype("int64")` is 1000x smaller |
| p2_dst_day_offset | pandas 2.3.3 -> 3.0.6 | `Timestamp + Day(n)` across DST: 24 h becomes a calendar day |
| p3_groupby_report | pandas 2.3.3 -> 3.0.6 | categorical `groupby` drops empty categories; `apply` loses the grouping column |
| p4_label_histogram | pandas 2.3.3 -> 3.0.6 | `astype(str)` keeps None/NaN as NaN; `DataFrame.value_counts(sort=False)` order |
| n6_uint8_scaling | NumPy 1.26.4 -> 2.5.4 | uint8 scalar arithmetic wraps around |
| n7_float32_scalars | NumPy 1.26.4 -> 2.5.4 | float32 scalar * Python float stays float32 (sum digits, comparisons) |
| p5_chained_assignment | pandas 2.3.3 -> 3.0.6 | chained assignment `df[col][mask] = v` no longer modifies `df`; only a `ChainedAssignmentError` warning is emitted, no exception |
| p6_str_dtype_checks | pandas 2.3.3 -> 3.0.6 | string columns become `str` dtype (`dtype == object` is False), missing values are NaN, not None |
| n8_string_to_bool | NumPy 1.26.4 -> 2.5.4 | `astype(bool)` on strings: non-empty means True, so "0" becomes True |
| p7_censor_chained_iloc | pandas 2.3.3 -> 3.0.6 | chained `df['Censoring'].iloc[i] = v` in scikit-FIBERS `censor`: the write is lost, so the `Censoring` column is not updated |
| p8_session_report_three_breaks | pandas 2.3.3 -> 3.0.6 | three breaks in one function: epoch seconds 1000x smaller, chained assignment, None versus NaN |
| n9_fleet_report_three_breaks | NumPy 1.26.4 -> 2.5.4 | three breaks in one function: string to bool, uint8 wrap-around, float32 promotion |

p5, p6, n8, p8 and n9 are our own reproductions derived from documented behavior changes (pandas 3.0.0 and NumPy 2.0.0 release notes; the uint8 and float32 values in n9 were measured by us, see `docs/CASES.md`), not incidents from real projects; the sources and their caveats are in `docs/CASES.md`. For p2, p3 and p4 no real project incident was found either.

A case is counted only if `python -m patchpilot.validate_case benchmarks/<case>` reports it valid (old OK, new silently broken, tests green on both, hidden inputs break too, known-good patch accepted, known-bad patches rejected).

