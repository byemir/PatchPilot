from app import censor_records


def test_keeps_every_row_and_marks_with_zero_or_one():
    rows = [{"id": 1, "Duration": 5.0}, {"id": 2, "Duration": 9.0}, {"id": 3, "Duration": 2.5}, {"id": 4, "Duration": 7.0}]
    out = censor_records(rows, 0.5, 3)
    assert sorted(r[0] for r in out) == [1, 2, 3, 4]
    assert all(r[2] in (0, 1) for r in out)
