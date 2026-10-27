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
