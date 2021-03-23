from cloudbot.util import sequence


def test_chunk_iter():
    assert len(list(sequence.chunk_iter([1, 2, 3, 4, 5, 6, 7, 8, 9], 2))) == 5
