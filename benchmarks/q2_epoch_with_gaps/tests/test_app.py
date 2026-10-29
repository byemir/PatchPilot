import json
from pathlib import Path

from app import epoch_with_gaps


def test_runs_on_the_recorded_inputs():
    probes = json.loads((Path(__file__).resolve().parent.parent / "inputs.json").read_text())
    for probe in probes:
        json.dumps(epoch_with_gaps(**probe))
