from app import label_histogram


def test_counts_repeated_pairs():
    out = label_histogram([["t1", "a"], ["t1", "a"], ["t2", "b"]])
    assert sorted(out) == [["t1", "a", 2], ["t2", "b", 1]]


def test_rows_are_triples():
    assert all(len(r) == 3 for r in label_histogram([["t1", "a"]]))
