from cloudbot.util import database


def test_database(mock_db):
    database.configure()
    assert database.Session().bind is None
    engine = mock_db.engine
    database.configure(engine)
    assert database.Session().bind is engine
