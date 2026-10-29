#!/bin/bash
# Runs the six fixed queries of docs/REAL_CASES_PROTOCOL.md (Amendment 1) and stores the raw results.
#   bash scripts/real_case_search.sh      (needs `gh auth login`)
cd "$(dirname "$0")/.." || exit 1
D=docs/real_cases/search_$(date +%Y%m%d)_run2; mkdir -p "$D"
Q1='"chained assignment" "pandas 3.0"'
Q2='"copy-on-write" "pandas 3.0"'
Q3='"pandas 3.0" astype datetime'
Q4='"numpy 2.0" "type promotion"'
Q5='"numpy 2.0" uint8 overflow'
Q6='"pandas 3.0" "str dtype"'
for i in 1 2 3 4 5 6; do
  q="Q$i"; eval "query=\$$q"
  printf '%s\t%s\n' "$q" "$query" >> "$D/queries.tsv"
  gh api -X GET search/issues -f q="$query is:closed language:python" -f per_page=30 \
    --jq '.items[] | [(.repository_url | sub("https://api.github.com/repos/"; "")), .number, (if .pull_request then "PR" else "issue" end), .created_at[:10], .title, .html_url] | @tsv' \
    > "$D/$q.tsv" 2> "$D/$q.err"
  echo "$q: $(wc -l < "$D/$q.tsv") hits $(head -c 200 "$D/$q.err")"
  sleep 3
done
cut -f1 "$D"/Q*.tsv | sort -u | while read -r repo; do
  info=$(gh api "repos/$repo" --jq '[.license.spdx_id // "none", .stargazers_count, .pushed_at[:10], .archived] | @tsv' 2>/dev/null)
  printf '%s\t%s\n' "$repo" "${info:-unavailable}"
done > "$D/repos.tsv"
echo "written to $D"; wc -l "$D/repos.tsv"
