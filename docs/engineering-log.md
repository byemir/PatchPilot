# Engineering log

## 2026-10-27
- Setup: system Python is 3.14, which cannot host both old and new library sides. Use a dedicated Python 3.12 interpreter and one venv per library version under .sandboxes/ (git-ignored).
- Mistake and fix: overwriting .gitignore with a short printf wiped the GitHub template (218 lines). Restored it from the previous commit. Lesson: inspect repo contents before writing files that a template may already provide.
- Case p1_epoch_seconds: pandas 3.0 infers datetime64[us] where 2.x gave [ns], so astype("int64") returns values 1000x smaller. Tests that only check types stay green; a recorded golden output catches it.
- Correction: the claim that Python 3.14 cannot host both library sides was an unverified assumption. Verified only that Python 3.12 can install both pandas 2.3.3 and 3.0.6.
- Observed: pandas 3.0.6 returns [1711107, 1711152] vs golden [1711107360, 1711152000]; pytest passes on both, so the breakage is silent.
- Added patchpilot/sandbox.py (isolated subprocess with wall-clock and CPU limits, minimal env) and patchpilot/check.py (verdicts: OK, LOUD_FAILURE, SILENT_BREAKAGE, RUN_ERROR). Verified: p1_epoch_seconds is OK on pandas 2.3.3 and SILENT_BREAKAGE on 3.0.6.
- Design fix: use os.path.abspath instead of Path.resolve for the interpreter path, because a venv python is a symlink and resolving it would likely bypass the venv (not reproduced, avoided by design).
- Known gaps: no memory limit and no network isolation on this local runner (macOS); planned for the Modal Sandboxes runner.
- Added patchpilot/sandbox.py (isolated subprocess with wall-clock and CPU limits, minimal env) and patchpilot/check.py (verdicts: OK, LOUD_FAILURE, SILENT_BREAKAGE, RUN_ERROR). Verified: p1_epoch_seconds is OK on pandas 2.3.3 and SILENT_BREAKAGE on 3.0.6.
- Design fix: use os.path.abspath instead of Path.resolve for the interpreter path, because a venv python is a symlink and resolving it would likely bypass the venv (not reproduced, avoided by design).
- Known gaps: no memory limit and no network isolation on this local runner (macOS); planned for the Modal Sandboxes runner.
- Meta Model API reachable from Turkey with a hackathon key. GET /v1/models lists muse-spark-1.3, muse-wonder-1.0 and -contributor variants (training-use tier, avoided by policy).
- Assumption corrected: a third-party doc claimed keys have the form LLM|id|secret; ours has no pipe characters. Do not validate key format client-side, let the API decide.
- Added patchpilot/meta_client.py: stdlib-only Chat Completions client with a fixed base URL so the key can never be sent elsewhere.
- First end-to-end loop (patchpilot/agent.py): muse-spark-1.3 (reasoning_effort=low) repaired p1_epoch_seconds in 1 attempt, 2608 tokens. Patch verified OK on pandas 2.3.3 and 3.0.6 against the recorded golden output.
- Guardrails: tests, run_case.py and golden.json are read-only for the agent; every attempt is recorded under runs/ (git-ignored).
- Open concern: the patch subtracts a tz-naive epoch, which likely breaks on tz-aware input; the case only covers one recorded input set. To be confirmed by an experiment, then covered by extra probe inputs.
- Single case, single run: not a benchmark result.
