from app import schedule


def test_shapes():
    out = schedule("2024-06-01 09:00", "Europe/Istanbul", 1, 3)
    assert len(out["one_by_one"]) == 3
    assert len(out["as_index"]) == 3
    assert all(isinstance(s, str) for s in out["one_by_one"] + out["as_index"])


def test_first_item_is_start():
    out = schedule("2024-06-01 09:00", "UTC", 2, 2)
    assert out["one_by_one"][0].startswith("2024-06-01 09:00")
