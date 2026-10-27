from app import weighted_score


def test_shape():
    total, hits = weighted_score([1.0, 2.0, 3.0], 2.0, 3.0)
    assert isinstance(hits, int)
    assert abs(total - 12.0) < 1e-3


def test_empty():
    assert weighted_score([], 1.5, 0.0) == [0.0, 0]
