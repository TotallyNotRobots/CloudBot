from cloudbot.util.database import base, metadata


def test_database():
    assert metadata is None
    assert base is None
