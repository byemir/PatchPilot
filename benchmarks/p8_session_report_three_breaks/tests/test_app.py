from app import session_report


def test_one_row_per_event_in_order():
    events = [{"user": "a", "ts": "2024-03-01 10:00:00", "amount": 5.0, "note": "x"},
              {"user": "b", "ts": "2024-03-02 11:00:00", "amount": 9.0, "note": None}]
    out = session_report(events, 6.0)
    assert [r[0] for r in out["rows"]] == ["a", "b"]
    assert out["last_epoch"] == max(r[1] for r in out["rows"])
