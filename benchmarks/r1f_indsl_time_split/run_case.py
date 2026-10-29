import json
import sys

from tests.adapter import split_series

path = sys.argv[1] if len(sys.argv) > 1 else "inputs.json"
with open(path) as f:
    probes = json.load(f)

out = []
for probe in probes:
    try:
        out.append(split_series(**probe))
    except Exception as e:
        out.append({"error": type(e).__name__})
print(json.dumps(out))
