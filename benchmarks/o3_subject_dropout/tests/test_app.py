import json
from pathlib import Path

from app import mark_dropouts


def test_runs_on_the_recorded_inputs():
    probes = json.loads((Path(__file__).resolve().parent.parent / "inputs.json").read_text())
    for probe in probes:
        json.dumps(mark_dropouts(**probe))
