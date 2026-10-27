from app import total_brightness


def test_returns_non_negative_int():
    out = total_brightness([10, 20, 30], 2)
    assert isinstance(out, int)
    assert out >= 0
