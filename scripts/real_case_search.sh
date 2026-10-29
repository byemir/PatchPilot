#!/bin/bash
# Runs the six fixed queries of docs/REAL_CASES_PROTOCOL.md and stores the raw results.
#   bash scripts/real_case_search.sh      (needs `gh auth login`)
cd "$(dirname "$0")/.." || exit 1
D=docs/real_cases/search_$(date +%Y%m%d); mkdir -p "$D"
Q1='"chained assignment" "pandas 3"'
Q2='"copy-on-write" "pandas 3"'
Q3='"pandas 3.0" astype datetime'
Q4='"numpy 2" "NEP 50"'
Q5='"numpy 2.0" uint8 overflow'
Q6='"pandas 3" "str dtype"'
for i in 1 2 3 4 5 6; do
  q="Q$i"; eval "query=\$$q"
  printf '%s\t%s\n' "$q" "$query" >> "$D/queries.tsv"
  gh search issues --state closed --language python --limit 30 --json repository,number,isPullRequest,title,url,createdAt \
    --jq '.[] | [.repository.nameWithOwner, .number, (if .isPullRequest then "PR" else "issue" end), .createdAt[:10], .title, .url] | @tsv' \
    -- "$query" > "$D/$q.tsv" 2> "$D/$q.err"
  echo "$q: $(wc -l < "$D/$q.tsv") hits $(head -c 200 "$D/$q.err")"
  sleep 3
done
cut -f1 "$D"/Q*.tsv | sort -u | while read -r repo; do
  info=$(gh api "repos/$repo" --jq '[.license.spdx_id // "none", .stargazers_count, .pushed_at[:10], .archived] | @tsv' 2>/dev/null)
  printf '%s\t%s\n' "$repo" "${info:-unavailable}"
done > "$D/repos.tsv"
echo "written to $D"; wc -l "$D/repos.tsv"
