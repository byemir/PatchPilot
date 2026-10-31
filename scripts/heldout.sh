#!/usr/bin/env bash
# Held-out run of the chain (docs/census/PREREGISTERED4.txt). Usage: bash scripts/heldout.sh WORKDIR
# Needs the pinned environments (scripts/setup_envs.sh) and a key file for the model. WORKDIR must be outside this repository.
set -u
W="${1:?usage: bash scripts/heldout.sh WORKDIR}"
MODEL="${MODEL:-meta-models/muse-spark-open-1026}"
cd "$(dirname "$0")/.."
case "$(cd "$W" 2>/dev/null && pwd || echo "$W")" in "$PWD"*) echo "WORKDIR must be outside the repository" >&2; exit 2;; esac
mkdir -p "$W"
while read -r name url; do
  [ -n "$name" ] || continue
  d="$W/$name"
  echo "== $name"
  if [ ! -d "$d/.git" ]; then
    timeout 180 git clone --depth 1 -q "$url" "$d" || { echo "$name: clone failed" | tee "$W/$name.failed"; continue; }
  fi
  git -C "$d" rev-parse HEAD > "$W/$name.commit"
  python3 -m patchpilot.discover "$d" --limit 10 --json "$W/$name.discover.json" --manifest "$W/$name.scan.json" --probes-dir "$W/$name.probes" > "$W/$name.discover.txt" 2>&1
  tail -n 3 "$W/$name.discover.txt" | cut -c1-200
  [ -f "$W/$name.scan.json" ] || { echo "$name: no candidates"; continue; }
  env -i HOME="$HOME" PATH="$PATH" TMPDIR=/tmp python3 -m patchpilot.propose "$W/$name.scan.json" --model "$MODEL" --effort low > "$W/$name.propose.txt" 2>&1
  tail -n 2 "$W/$name.propose.txt" | cut -c1-200
  env -i HOME="$HOME" PATH="$PATH" TMPDIR=/tmp python3 -m patchpilot.scan "$W/$name.scan.json" --model "$MODEL" --effort low --out-dir "$W/out_$name" > "$W/$name.scan.txt" 2>&1
  tail -n 3 "$W/$name.scan.txt" | cut -c1-200
done <<'LIST'
abu https://github.com/bbfamily/abu
modin https://github.com/modin-project/modin
pytimetk https://github.com/business-science/pytimetk
pygraphistry https://github.com/graphistry/pygraphistry
siuba https://github.com/machow/siuba
hamilton https://github.com/stitchfix/hamilton
pandera https://github.com/unionai-oss/pandera
django-rest-pandas https://github.com/wq/django-rest-pandas
LIST
python3 scripts/heldout_summary.py "$W"
