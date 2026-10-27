# Engineering log

## 2026-10-27
- Setup: system Python is 3.14, which cannot host both old and new library sides. Use a dedicated Python 3.12 interpreter and one venv per library version under .sandboxes/ (git-ignored).
- Mistake and fix: overwriting .gitignore with a short printf wiped the GitHub template (218 lines). Restored it from the previous commit. Lesson: inspect repo contents before writing files that a template may already provide.
- Case p1_epoch_seconds: pandas 3.0 infers datetime64[us] where 2.x gave [ns], so astype("int64") returns values 1000x smaller. Tests that only check types stay green; a recorded golden output catches it.
