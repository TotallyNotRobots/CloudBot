from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


class MockDB:
    def __init__(self):
        self.engine = create_engine("sqlite:///:memory:")
        self.session = scoped_session(sessionmaker(self.engine))

    def get_data(self, table):
        return self.session().execute(table.select()).fetchall()

    def add_row(self, *args, **data):
        table = args[0]
        self.session().execute(table.insert().values(data))
        self.session().commit()


@pytest.fixture()
def mock_db():
    return MockDB()


@pytest.fixture
def patch_paste():
    with patch("cloudbot.util.web.paste") as mock:
        yield mock


@pytest.fixture()
def patch_try_shorten():
    with patch("cloudbot.util.web.try_shorten", new=lambda x: x):
        yield


@pytest.fixture()
def unset_bot():
    try:
        yield
    finally:
        from cloudbot.bot import bot

        bot.set(None)
