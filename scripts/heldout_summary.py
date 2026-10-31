"""Table of a held-out run (see docs/census/PREREGISTERED4.txt): python3 scripts/heldout_summary.py WORKDIR"""
import json
import sys
from pathlib import Path

NAMES = ["abu", "modin", "pytimetk", "pygraphistry", "siuba", "hamilton", "pandera", "django-rest-pandas"]


def load(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def main(argv):
    w = Path(argv[1])
    print("| repository | commit | candidates | sites skipped | got inputs | healthy | silent | loud | invalid | repaired | repair tokens |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for n in NAMES:
        commit = (w / f"{n}.commit").read_text().strip()[:7] if (w / f"{n}.commit").exists() else "clone failed"
        d = load(w / f"{n}.discover.json")
        cands = d["total_candidates"] if d else 0
        skipped = sum((d or {}).get("skipped", {}).values())
        man = load(w / f"{n}.scan.json")
        targets = man["targets"] if man else []
        got = sum(1 for t in targets if not t.get("placeholder"))
        rep = load(w / f"out_{n}" / "scan_report.json")
        c = (rep or {}).get("counts", {})
        tok = (rep or {}).get("tokens", 0)
        print(f"| {n} | {commit} | {cands} | {skipped} | {got} | {c.get('healthy', 0)} | {c.get('silent', 0) + c.get('repaired', 0) + c.get('not_repaired', 0)} | {c.get('loud', 0)} | {c.get('invalid', 0)} | {c.get('repaired', 0)} | {tok} |")
    print("\nsilent = silent before repair (repaired and not repaired included). healthy holds for the inputs used. One run each.")


if __name__ == "__main__":
    main(sys.argv)
