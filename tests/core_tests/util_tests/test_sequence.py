import string


def test_chunk_iter():
    from cloudbot.util.sequence import chunk_iter
    it = chunk_iter(list(string.ascii_letters), 4)
    assert len(list(it)) == 52 / 4
