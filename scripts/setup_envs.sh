#!/usr/bin/env bash
# Builds the four sandbox venvs (old/new library sides) with pinned versions,
# then validates every benchmark case. Needs only Python 3.12, venv and pip.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON312:-$(command -v python3.12 || true)}"
[ -n "$PY" ] || { echo "Python 3.12 not found. Set PYTHON312=/path/to/python3.12" >&2; exit 1; }
mk() {
  name="$1"; shift
  [ -x ".sandboxes/$name/bin/python" ] || "$PY" -m venv ".sandboxes/$name"
  ".sandboxes/$name/bin/python" -m pip install -q "$@" pytest==9.1.1
}
mk np126 numpy==1.26.4
mk np2   numpy==2.5.4
mk pd23  numpy==2.5.4 pandas==2.3.3
mk pd30  numpy==2.5.4 pandas==3.0.6
for c in benchmarks/*/; do "$PY" -m patchpilot.validate_case "${c%/}"; done
