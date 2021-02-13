def test_chunk_iter():
    from cloudbot.util.sequence import chunk_iter

    assert len(list(chunk_iter([1, 2, 3, 4, 5, 6, 7, 8, 9], 2))) == 5
