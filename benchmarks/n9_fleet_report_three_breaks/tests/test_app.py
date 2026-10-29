from app import fleet_report


def test_one_row_per_device_and_count_matches():
    devices = [{"flag": "1", "level": 10}, {"flag": "0", "level": 20}, {"flag": "1", "level": 30}]
    out = fleet_report(devices, 1.0)
    assert len(out["rows"]) == 3
    assert out["enabled"] == sum(r[0] for r in out["rows"])
