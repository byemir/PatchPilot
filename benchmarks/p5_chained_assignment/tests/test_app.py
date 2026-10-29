from app import apply_discounts


def test_keeps_rows_and_order():
    rows = [[1, 120.0, "open"], [2, 80.0, "open"]]
    out = apply_discounts(rows, 100.0, 0.1)
    assert [r[0] for r in out] == [1, 2]
    assert all(len(r) == 3 for r in out)
