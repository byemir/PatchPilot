#!/usr/bin/env bash
# Builds a demo folder for the app: the shop example plus the real traceml function (polyaxon/traceml, Apache-2.0).
# Needs Python 3.12, git and internet (a minute or two). The third-party code is cloned into the demo folder only, never into this repository.
#   PYTHON312=/path/to/python3.12 bash scripts/setup_demo_root.sh [DEMO_DIR]      (default DEMO_DIR: /tmp/pp_demo)
#   python -m patchpilot.app --root /tmp/pp_demo
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON312:-$(command -v python3.12 || true)}"
[ -n "$PY" ] || { echo "Python 3.12 not found. Set PYTHON312=/path/to/python3.12" >&2; exit 1; }
D="${1:-/tmp/pp_demo}"
COMMIT=2452c1a8f2be742a8a3b8e379568a6ce3bf4394c
rm -rf "$D"; mkdir -p "$D"
cp -R examples/shop "$D/shop"
cp -R examples/real_project_traceml "$D/real_project_traceml"
rm -f "$D/real_project_traceml/result.json"
# the project at the commit we ran (shallow fetch of that commit only)
mkdir -p "$D/rp_traceml"
( cd "$D/rp_traceml" && git init -q && git remote add origin https://github.com/polyaxon/traceml && git fetch -q --depth 1 origin "$COMMIT" && git checkout -q FETCH_HEAD )
# the two interpreters named in the manifest: pandas 2.3.3 and 3.0.6, NumPy 2, the project's one extra import, pytest
for pair in "old pandas==2.3.3" "new pandas==3.0.6"; do
  set -- $pair
  [ -x "/tmp/tm_$1/bin/python" ] || "$PY" -m venv "/tmp/tm_$1"
  "/tmp/tm_$1/bin/python" -m pip install -q 'numpy>=2,<3' "$2" clipped pytest
done
/tmp/tm_old/bin/python -c "import pandas, clipped; print('old interpreter: pandas', pandas.__version__)"
/tmp/tm_new/bin/python -c "import pandas, clipped; print('new interpreter: pandas', pandas.__version__)"
echo "Demo folder ready: $D"
echo "Start the app with:  python -m patchpilot.app --root $D"
