from app import clean_labels


def test_returns_rows_in_order():
    out = clean_labels([["A", "x", 1], ["B", "y", 2]])
    assert len(out["rows"]) == 2
    assert [r[2] for r in out["rows"]] == [1, 2]
