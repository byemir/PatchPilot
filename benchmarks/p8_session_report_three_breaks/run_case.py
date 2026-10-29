import json
import sys
import warnings

warnings.simplefilter("ignore")

from app import session_report

path = sys.argv[1] if len(sys.argv) > 1 else "inputs.json"
with open(path) as f:
    probes = json.load(f)

out = []
for probe in probes:
    try:
        out.append(session_report(probe["events"], probe["cutoff"]))
    except Exception as e:
        out.append({"error": type(e).__name__})
print(json.dumps(out))
