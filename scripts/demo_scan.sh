#!/bin/bash
# Demo of the scan command: check the eight functions of examples/sample_repo (written for this project) on the old and the new library
# and repair the silently broken ones with a local open-weight model. Needs the local server from the README
# (llama-server on 127.0.0.1:8080). No API key is used. Works on a copy; the repository is never changed.
#   bash scripts/demo_scan.sh            then:   python -m patchpilot.view <the report path printed at the end>
cd "$(dirname "$0")/.." || exit 1
curl -sf http://127.0.0.1:8080/health >/dev/null || { echo "local server not running; start llama-server as in the README first"; exit 1; }
D=$(mktemp -d); cp -R examples/sample_repo "$D/repo"
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=$(command -v python3); fi
env -i HOME="$HOME" PATH="$PATH" TMPDIR="${TMPDIR:-/tmp}" LANG="${LANG:-en_US.UTF-8}" USER="$USER" LOGNAME="${LOGNAME:-$USER}" TERM="${TERM:-xterm}" \
  $PY -m patchpilot.scan "$D/repo/scan.json" --endpoint http://127.0.0.1:8080/v1 --out-dir "$D/out"
echo "exit code: $?  (0 = every silently broken function was repaired; the copy in $D/repo was not changed)"
echo "view: $PY -m patchpilot.view $D/out/scan_report.json"
