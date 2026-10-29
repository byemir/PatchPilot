#!/bin/bash
# Demo: build a repair case from a real function (scikit-FIBERS censor) and repair it with a local open-weight model.
# Needs the local server from the README (llama-server on 127.0.0.1:8080). No API key is used.
#   bash scripts/demo_own_function.sh [low|medium]
cd "$(dirname "$0")/.." || exit 1
EFFORT="${1:-low}"
OLD=.sandboxes/pd23/bin/python; NEW=.sandboxes/pd30/bin/python
curl -sf http://127.0.0.1:8080/health >/dev/null || { echo "local server not running; start llama-server as in the README first"; exit 1; }
OUT=$(mktemp -d)/case
echo "== 1/3  build a case from the original function (pandas 2.3 -> 3.0)"
.venv/bin/python -m patchpilot.make_case --src examples/own_function/censor_adapter.py --fn censor_records \
  --inputs examples/own_function/probes.json --old $OLD --new $NEW --lib pandas --out "$OUT" || exit 1
echo; echo "== 2/3  repair with Muse Glimmer (local, effort $EFFORT)"
env -i HOME="$HOME" PATH="$PATH" TMPDIR="${TMPDIR:-/tmp}" LANG="${LANG:-en_US.UTF-8}" USER="$USER" LOGNAME="${LOGNAME:-$USER}" TERM="${TERM:-xterm}" \
  .venv/bin/python -m patchpilot.agent "$OUT" $OLD $NEW --lib pandas --model muse-glimmer --effort "$EFFORT" --endpoint http://127.0.0.1:8080/v1
echo; echo "== 3/3  done (run folder is under runs/)"
