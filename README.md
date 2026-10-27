# PatchPilot
Autonomous agent that repairs Python projects broken by dependency upgrades, focusing on **silent** behavior changes: the tests stay green, the output is wrong. Built during the Meta Global AI Developer Hackathon (Oct 26 - Nov 4, 2026).

## How it works
For each case the agent receives the broken program, the old and the new library environment, and proposes a patch. A patch is accepted only if all three gates pass:

1. **Visible check:** the recorded inputs reproduce the golden output (generated with the OLD library).
2. **Hidden check:** held-out inputs that are never shown to the model.
3. **Differential check:** generated inputs run through the original code on the old library and the patched code on the new one; core divergences reject the patch.

Defaults: up to 3 attempts per run, 60000 token budget. Patched code runs in an isolated subprocess (`patchpilot/sandbox.py`) with wall-clock and CPU limits and a minimal environment without inherited secrets. Known gap: no memory limit and no network isolation on the local runner.

## Setup
Requires Python 3.12 (tested with 3.12.16). One command builds four pinned virtual environments under `.sandboxes/` and validates all cases:

    PYTHON312=/path/to/python3.12 ./scripts/setup_envs.sh

A case is valid only if the old library is OK, the new one silently breaks, tests are green on both, hidden inputs break too, the known-good patch is accepted and the known-bad patches are rejected. Validation of a single case:

    python -m patchpilot.validate_case benchmarks/p1_epoch_seconds

## Run the agent
    export MODEL_API_KEY=...   # never commit it
    python -m patchpilot.agent benchmarks/p1_epoch_seconds .sandboxes/pd23/bin/python .sandboxes/pd30/bin/python

Cases n6/n7 use `.sandboxes/np126` and `.sandboxes/np2`. Benchmark runner: `python -m patchpilot.bench --help`.

## Limitations
All cases are synthetic and have not been tried on real open-source projects. Sample sizes in `results/` are small (n=5 per case and setting), so they show direction only.

Engineering log and technical notes: [`docs/engineering-log.md`](docs/engineering-log.md), [`docs/training-notes.jsonl`](docs/training-notes.jsonl).

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

