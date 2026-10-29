import json
import sys

from app import bars_to_epoch

path = sys.argv[1] if len(sys.argv) > 1 else "inputs.json"
with open(path) as f:
    probes = json.load(f)

out = []
for probe in probes:
    try:
        out.append(bars_to_epoch(**probe))
    except Exception as e:
        out.append({"error": type(e).__name__})
print(json.dumps(out))
