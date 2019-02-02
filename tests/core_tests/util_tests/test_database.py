

def test_database():
    import sys
    # Make sure we start with a fresh module
    sys.modules.pop('cloudbot.util.database', None)
    from cloudbot.util.database import metadata, base
    assert metadata is None
    assert base is None
