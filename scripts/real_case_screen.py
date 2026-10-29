"""First, mechanical screening of the raw search results (docs/REAL_CASES_PROTOCOL.md). Writes docs/real_cases/candidates.md.
Rules (criterion order): C2 license must be MIT, BSD-2-Clause, BSD-3-Clause or Apache-2.0 (NOASSERTION = unclear, checked by hand);
C4 the hit must be a project fix: dependency bumps, automated updates, and docs/test/CI-only titles are rejected.
Everything else is marked `inspect` and decided by reading the issue or pull request."""
import glob, re
D = sorted(glob.glob("docs/real_cases/search_*_run2"))[-1]
PERM = {"MIT", "BSD-2-Clause", "BSD-3-Clause", "Apache-2.0"}
BUMP = re.compile(r"\bbump\b|update dependency|update .{0,40}requirement|scheduled daily dependency|\[aikido\]|renovate|chore\(deps|deps\(deps|update .{0,30} to v\d|dependency update|update pandas|upgrade pandas|update numpy|update dependencies", re.I)
DOCS = re.compile(r"^(DOC|DOCS|TST|TEST|CI|BLD|STY)\b|^(docs|test|tests|ci|build)(\(|:)", re.I)
repos = {}
for line in open(f"{D}/repos.tsv"):
    p = line.rstrip("\n").split("\t"); repos[p[0]] = p[1] if len(p) > 1 else "unavailable"
rows, seen = [], {}
for qi in range(1, 7):
    for rank, line in enumerate(open(f"{D}/Q{qi}.tsv"), 1):
        f = line.rstrip("\n").split("\t")
        if len(f) < 6: continue
        repo, num, typ, date, title, url = f[:6]
        k = (repo, num)
        if k in seen: seen[k]["also"].append(f"Q{qi}#{rank}"); continue
        r = dict(q=f"Q{qi}#{rank}", repo=repo, num=num, typ=typ, date=date, title=title, url=url, also=[], lic=repos.get(repo, "unavailable"))
        if r["lic"] not in PERM and r["lic"] != "NOASSERTION":
            r["dec"], r["why"] = "rejected", f"C2: license {r['lic']} is not MIT/BSD/Apache"
        elif BUMP.search(title):
            r["dec"], r["why"] = "rejected", "C4: dependency bump or automated update, no project code fix in the title"
        elif DOCS.search(title):
            r["dec"], r["why"] = "rejected", "C3/C4: documentation, test or CI change only"
        else:
            r["dec"], r["why"] = "inspect", "license unclear (NOASSERTION), check by hand" if r["lic"] == "NOASSERTION" else "passes the mechanical screen"
        seen[k] = r; rows.append(r)
n_ins = sum(r["dec"] == "inspect" for r in rows)
out = ["# Candidates (run 2 of the fixed queries)", "",
       f"{len(rows)} distinct hits from {D}; {n_ins} passed the mechanical screen and are decided by hand below. Rules: `scripts/real_case_screen.py`. A hit found by several queries is listed once, at its first position.", "",
       "| first seen | hit | type | license | decision | reason |", "|---|---|---|---|---|---|"]
for r in rows:
    also = (" (also " + ", ".join(r["also"]) + ")") if r["also"] else ""
    out.append(f"| {r['q']}{also} | [{r['repo']}#{r['num']}]({r['url']}) {r['title'][:70].replace('|', '/')} | {r['typ']} | {r['lic']} | {r['dec']} | {r['why']} |")
open("docs/real_cases/candidates.md", "w").write("\n".join(out) + "\n")
print(len(rows), "distinct hits;", n_ins, "to inspect")
for r in rows:
    if r["dec"] == "inspect": print(f"{r['q']:7} {r['repo']}#{r['num']} {r['typ']} [{r['lic']}] {r['title'][:90]}")
