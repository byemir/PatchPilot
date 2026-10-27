from app import category_report


def test_one_row_per_category():
    out = category_report([["a", 1], ["b", 2], ["a", 3]], ["a", "b", "c"])
    assert [r[0] for r in out][:2] == ["a", "b"]
    assert all(len(r) == 4 for r in out)


def test_totals_of_observed_categories():
    out = category_report([["a", 1], ["b", 2], ["a", 3]], ["a", "b"])
    assert out[0][1] == 4 and out[1][1] == 2
