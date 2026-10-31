#!/bin/bash
# Runs every offline test (no model call, no real key, no network beyond loopback). Exit code 1 if any fails.
#   bash scripts/run_offline_tests.sh
cd "$(dirname "$0")/.." || exit 1
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=$(command -v python3); fi  # no .venv needed: the runner uses only the standard library
for e in np126 np2 pd23 pd30; do
  if [ ! -x ".sandboxes/$e/bin/python" ]; then
    echo "The pinned library environments are missing (.sandboxes/$e)." >&2
    echo "Build them once (needs Python 3.12 and internet, a few minutes):" >&2
    echo "  PYTHON312=/path/to/python3.12 ./scripts/setup_envs.sh" >&2
    exit 2
  fi
done
tests=(
  "patchpilot.local_test"
  "patchpilot.hosted_test"
  "patchpilot.tools_test"
  "patchpilot.make_case_test"
  "patchpilot.repair_test"
  "patchpilot.scan_test"
  "patchpilot.view_test"
  "patchpilot.app_test"
  "patchpilot.capture_test"
  "patchpilot.census_test"
  "patchpilot.discover_test"
  "patchpilot.propose_test"
  "patchpilot.runner_test"
  "patchpilot.suggest_test"
  "patchpilot.frames_test"
  "patchpilot.project_test"
  "patchpilot.isolation_test"
  "patchpilot.landlock_test"
  "patchpilot.gen2_test"
  "patchpilot.negative_test benchmarks/n8_string_to_bool"
)
fail=0; rows=()
for t in "${tests[@]}"; do
  start=$(date +%s)
  out=$(env -i HOME="$HOME" PATH="$PATH" TMPDIR="${TMPDIR:-/tmp}" LANG="${LANG:-en_US.UTF-8}" USER="$USER" LOGNAME="${LOGNAME:-$USER}" TERM="${TERM:-xterm}" $PY -m $t 2>&1)
  rc=$?
  secs=$(( $(date +%s) - start ))
  if [ $rc -eq 0 ]; then status="PASS"; else status="FAIL"; fail=1; echo "$out" | tail -n 15; fi
  rows+=("$(printf '%-4s %4ss  %s' "$status" "$secs" "$t")")
done
echo "-----"
printf '%s\n' "${rows[@]}"
[ $fail -eq 0 ] && echo "all offline tests passed" || echo "SOME TESTS FAILED"
exit $fail
