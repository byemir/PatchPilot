from app import to_epoch_seconds


def test_returns_one_int_per_input():
    out = to_epoch_seconds(["2024-03-22 11:36", "2024-03-23 00:00"])
    assert len(out) == 2
    assert all(isinstance(x, int) for x in out)
