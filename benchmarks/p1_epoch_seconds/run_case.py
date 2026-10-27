import json

from app import to_epoch_seconds

print(json.dumps(to_epoch_seconds(["2024-03-22 11:36", "2024-03-23 00:00"])))
