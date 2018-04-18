

def test_database():
    from cloudbot.util.database import metadata, base
    assert metadata is None
    assert base is None
