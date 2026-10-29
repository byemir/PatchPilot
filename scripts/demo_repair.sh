#!/bin/bash
# Demo of the one-command tool: repair a real function (scikit-FIBERS censor, behind a thin adapter) with a local open-weight model.
# Needs the local server from the README (llama-server on 127.0.0.1:8080). No API key is used. Your copy of the file is never changed.
#   bash scripts/demo_repair.sh
cd "$(dirname "$0")/.." || exit 1
curl -sf http://127.0.0.1:8080/health >/dev/null || { echo "local server not running; start llama-server as in the README first"; exit 1; }
D=$(mktemp -d); cp examples/own_function/censor_adapter.py "$D/"
env -i HOME="$HOME" PATH="$PATH" TMPDIR="${TMPDIR:-/tmp}" LANG="${LANG:-en_US.UTF-8}" USER="$USER" LOGNAME="${LOGNAME:-$USER}" TERM="${TERM:-xterm}" \
  .venv/bin/python -m patchpilot.repair "$D/censor_adapter.py" censor_records --inputs examples/own_function/probes.json \
  --lib pandas --endpoint http://127.0.0.1:8080/v1 --out-dir "$D"
echo "exit code: $?  (0 = a patch passed the gates; the copy in $D was not changed)"
