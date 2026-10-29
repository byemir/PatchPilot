#!/bin/bash
# Demo of the one-command tool: repair an example function of ours (examples/own_function/subject_dropout.py) with a local open-weight model.
# Needs the local server from the README (llama-server on 127.0.0.1:8080). No API key is used. Your copy of the file is never changed.
#   bash scripts/demo_repair.sh
cd "$(dirname "$0")/.." || exit 1
curl -sf http://127.0.0.1:8080/health >/dev/null || { echo "local server not running; start llama-server as in the README first"; exit 1; }
D=$(mktemp -d); cp examples/own_function/subject_dropout.py "$D/"
env -i HOME="$HOME" PATH="$PATH" TMPDIR="${TMPDIR:-/tmp}" LANG="${LANG:-en_US.UTF-8}" USER="$USER" LOGNAME="${LOGNAME:-$USER}" TERM="${TERM:-xterm}" \
  .venv/bin/python -m patchpilot.repair "$D/subject_dropout.py" mark_dropouts --inputs examples/own_function/probes.json \
  --lib pandas --endpoint http://127.0.0.1:8080/v1 --out-dir "$D"
echo "exit code: $?  (0 = a patch passed the gates; the copy in $D was not changed)"
