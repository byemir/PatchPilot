from app import enabled_devices


def test_count_matches_flags():
    out = enabled_devices(["1", "0", "1"])
    assert out["count"] == sum(out["enabled"])
    assert len(out["enabled"]) == 3
