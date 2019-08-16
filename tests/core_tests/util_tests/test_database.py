import importlib

from cloudbot.util import database


def test_database():
    importlib.reload(database)
    assert database.metadata.bind is None
    assert database.base is None
