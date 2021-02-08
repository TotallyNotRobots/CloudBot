import datetime
from typing import Callable, Iterator, List
from unittest.mock import MagicMock

import freezegun
import pytest
from responses import RequestsMock
from sqlalchemy.orm import close_all_sessions

from cloudbot.bot import bot
from cloudbot.util import database
from tests.util.mock_bot import MockBot
from tests.util.mock_db import MockDB


@pytest.fixture()
def mock_db(tmp_path):
    db = MockDB("sqlite:///" + str(tmp_path / "database.db"))
    database.metadata.clear()
    database.configure(db.engine)
    yield db
    close_all_sessions()
    database.configure()
    database.metadata.clear()


@pytest.fixture()
def mock_bot_factory() -> Iterator[Callable[..., MockBot]]:
    instances: List[MockBot] = []

    def _factory(*args, **kwargs):
        _bot = MockBot(*args, **kwargs)
        instances.append(_bot)
        return _bot

    try:
        yield _factory
    finally:
        for b in instances:
            b.close()


@pytest.fixture()
def mock_bot(mock_bot_factory):
    yield mock_bot_factory()


@pytest.fixture()
def mock_requests():
    with RequestsMock() as reqs:
        yield reqs


@pytest.fixture()
def freeze_time():
    # Make sure some randomness in the time doesn't break a test
    dt = datetime.datetime(2019, 8, 22, 18, 14, 36)
    diff = datetime.datetime.now() - datetime.datetime.utcnow()
    ts = round(diff.total_seconds() / (15 * 60)) * (15 * 60)
    tz = datetime.timedelta(seconds=ts)

    with freezegun.freeze_time(dt, tz) as ft:
        yield ft


@pytest.fixture()
def mock_api_keys():
    try:
        bot.set(MagicMock())
        bot.config.get_api_key.return_value = "APIKEY"
        yield
    finally:
        bot.set(None)
