# PatchPilot
Autonomous agent that repairs Python projects broken by dependency upgrades, focusing on **silent** behavior changes: the tests stay green, the output is wrong. Built during the Meta Global AI Developer Hackathon (Oct 26 - Nov 4, 2026).

## How it works
For each case the agent receives the program source, the golden output (from the old library) and the actual output on the new library, and proposes a patch (one model call per attempt, JSON reply, no tool use; a rejected attempt returns feedback to the model). A patch is accepted only if all three gates pass:

1. **Visible check:** the recorded inputs reproduce the golden output (generated with the OLD library).
2. **Hidden check:** held-out inputs that are never shown to the model.
3. **Differential check:** generated inputs run through the original code on the old library and the patched code on both libraries; core divergences reject the patch.

Defaults: up to 3 attempts per run, 60000 token budget. The benchmark runner can switch the differential gate off (`--no-differential`) and score accepted patches with it afterwards at another seed (`--score-seed`). Patched code runs in a subprocess inside a temporary copy of the case (`patchpilot/sandbox.py`) with a wall-clock timeout (the process group is killed), a CPU-time limit and a minimal environment without inherited secrets. Model code runs on your machine with your user's privileges; this runner is not a hardened security boundary. On macOS, `bench` and `agent` additionally wrap model code in `sandbox-exec` (no read or write access to the home directory and the repository except the sandbox environments, no network), re-exec themselves with a minimal environment, read the API key from a file instead of the environment, and refuse to run model code if the harness environment holds secret-looking variables or the isolation self-test fails. Shown on one macOS machine with fake secrets (`patchpilot/isolation_test.py`, `patchpilot/negative_test.py`, details in the engineering log): a fake secret file under `~/.config`, the repository's `hidden_golden.json` (absolute path), a home directory listing and a loopback connection were blocked. Reading the harness's initial environment through `sysctl` was NOT blocked by the profile, which is why the environment must not hold secrets. Not tested: memory inspection tools (`lldb`, `vmmap`, `gcore`), other same-user processes that hold secrets, Linux, external network. On other platforms `bench` and `agent` are written to refuse to run unless `--no-fs-deny` is given (only the missing `sandbox-exec` case was tested); such runs are marked `fs_deny=false` and are not counted. There is no memory limit.

## Setup
Requires Python 3.12 (tested with 3.12.16). `PYTHON312` must point to a Python 3.12 interpreter; on the macOS machine used for development `python3.12` was not on `PATH`, so the path was passed explicitly. A fresh clone with this script built the four environments and reported all six cases valid. One command builds four pinned virtual environments under `.sandboxes/` and validates all cases:

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

## Limitations
All cases are synthetic and have not been tried on real open-source projects. Sample sizes in `results/` are small (1 to 5 runs per case and setting; the first three files have 3 runs per case, one smoke test has 1), so they show direction only. Only token counts were recorded, no dollar cost (official prices were not verified). The first two bench files and earlier runs ran without the differential gate (see the engineering log).

Engineering log and technical notes: [`docs/engineering-log.md`](docs/engineering-log.md), [`docs/training-notes.jsonl`](docs/training-notes.jsonl).

## Results so far

All numbers come from the files in `results/`. Cases are synthetic, samples are small, only token counts were recorded. The rows of the first table below were produced before the isolation layer existed: model code ran without the OS layer and the API key was in the process environment (none of the files in that table has an `fs_deny` field). The 126 patches in `runs/` at the time of the check import only pandas, numpy, collections and math (import lines only), so no sign of file or environment access was found; that scan cannot rule it out.

| setting | model | result | file |
|---|---|---|---|
| effort=minimal, differential gate on, 5 runs per case | muse-spark-1.3 | solved 25/30 runs: n6 5/5, n7 5/5, p1 5/5, p2 5/5, p3 5/5, p4 0/5 | `bench_20261027-185732_muse-spark-1.3.json` |
| p4 only, effort=low, gate on, 5 runs | muse-spark-1.3 | 0/5 | `bench_20261027-190705_muse-spark-1.3.json` |
| p4 only, effort=low, gate on, 5 runs | muse-wonder-1.0 | 1/5 | `bench_20261027-191341_muse-wonder-1.0.json` |
| p4 only, effort=low, gate off, accepted patches scored with the differential at seed 1 | muse-spark-1.3 | 2/5 accepted, 0 pass the differential | `bench_20261027-204730_muse-spark-1.3.json` |
| p4 only, effort=low, gate off, accepted patches scored with the differential at seed 1 | muse-wonder-1.0 | 3/5 accepted, 1 passes the differential | `bench_20261027-205730_muse-wonder-1.0.json` |

Observed in two wonder-1.0 runs (n=2; one before and one after the isolation layer): with the gate on, the differential rejected an attempt that had passed the visible and hidden checks, the counterexample was returned to the model and the next attempt passed. p4 is mostly unsolved; with the gate off, 4 of the 5 accepted patches failed the differential, which is why accepted counts and differential-scored counts are reported separately. Details and caveats: the engineering log.

## Results under the isolation layer

p4_label_histogram only, effort=low, 5 runs per model, differential used as a gate and accepted patches re-scored with the differential at another seed, one invocation per model (the result files have counted=true and fs_deny=true).

| model | solved | first try | accepted patches passing the re-scored differential | avg tokens | file |
|---|---|---|---|---|---|
| muse-spark-1.3 | 0/5 | 0 | 0 | 21230 | `bench_20261027-224719_muse-spark-1.3.json` |
| muse-wonder-1.0 | 3/5 | 1 | 3 of 3 | 13066 | `bench_20261027-225746_muse-wonder-1.0.json` |

First failing gate per attempt: spark-1.3 (15 attempts) visible 7, hidden 6, differential 2; wonder-1.0 (13 attempts) visible 6, hidden 3, differential 1, accepted 3. n=5 per model, one synthetic case; these runs differ from the earlier p4 rows, so this is not a controlled comparison. Only token counts were recorded.

## Tools mode (experimental, p4 only)

`--tools` lets the model call `run_tests` and `run_probe` during an attempt (one conversation per attempt, at most 12 tool calls, and the same 60000-token run budget, which is checked only before each model call and was exceeded in several runs). `run_probe` runs inputs chosen by the model through the original code on the old library and through the candidate on the new library; it is an oracle for the original behavior on those inputs. The gate is unchanged and is not available to the model.

p4_label_histogram, effort=low, 5 runs per model, differential used as a gate, accepted patches re-scored at another seed (result files have counted=true, tools=true, fs_deny=true):

| model | solved | first try | accepted patches passing the re-scored differential | runs ended by the token budget | avg tokens | file |
|---|---|---|---|---|---|---|
| muse-spark-1.3 | 2/5 | 1 | 2 of 2 | 3 | 53834 | `bench_20261028-094310_muse-spark-1.3_tools.json` |
| muse-wonder-1.0 | 2/5 | 1 | 2 of 2 | 3 | 67056 | `bench_20261028-095554_muse-wonder-1.0_tools.json` |

Same setting without tools (table above): spark 0/5 (avg 21230 tokens), wonder 3/5 (avg 13066). First failing gate per attempt, 16 attempts with tools: visible 2, hidden 0, differential 8, invalid reply 2, accepted 4; 28 attempts without tools: visible 13, hidden 9, differential 3, accepted 3. No run with tools reached a third attempt. Two of the four accepted patches were submitted from the last files passed to a tool after the token budget stopped the conversation. With tools, prompt tokens (the context is re-sent on every call) were 61 percent (spark) and 73 percent (wonder) of all tokens. n=5 per model, one synthetic case, runs differ: this pilot gives no evidence that the tools improve the success rate, and with the same budget they used 2.5 to 5.1 times the tokens per run. Only token counts were recorded.

## Benchmark cases

All cases are **synthetic**: small programs written for this project and derived from library release notes and from running both versions. They are not taken from real open-source projects. Each case keeps its recorded inputs (`inputs.json`, `golden.json`), held-out inputs that are never shown to the model (`hidden_inputs.json`, `hidden_golden.json`), a `known_good.json` patch and `known_bad/` patches. Golden outputs come from the OLD library version.

| case | library change (old -> new) | what silently changes |
|---|---|---|
| p1_epoch_seconds | pandas 2.3.3 -> 3.0.6 | datetime unit ns -> us, `astype("int64")` is 1000x smaller |
| p2_dst_day_offset | pandas 2.3.3 -> 3.0.6 | `Timestamp + Day(n)` across DST: 24 h becomes a calendar day |
| p3_groupby_report | pandas 2.3.3 -> 3.0.6 | categorical `groupby` drops empty categories; `apply` loses the grouping column |
| p4_label_histogram | pandas 2.3.3 -> 3.0.6 | `astype(str)` keeps None/NaN as NaN; `DataFrame.value_counts(sort=False)` order |
| n6_uint8_scaling | NumPy 1.26.4 -> 2.5.4 | uint8 scalar arithmetic wraps around |
| n7_float32_scalars | NumPy 1.26.4 -> 2.5.4 | float32 scalar * Python float stays float32 (sum digits, comparisons) |

A case is counted only if `python -m patchpilot.validate_case benchmarks/<case>` reports it valid (old OK, new silently broken, tests green on both, hidden inputs break too, known-good patch accepted, known-bad patches rejected).

