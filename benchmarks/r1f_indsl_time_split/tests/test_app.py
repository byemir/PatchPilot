import json
from pathlib import Path

from tests.adapter import split_series


def test_runs_on_the_recorded_inputs():
    probes = json.loads((Path(__file__).resolve().parent.parent / "inputs.json").read_text())
    for probe in probes:
        json.dumps(split_series(**probe))
