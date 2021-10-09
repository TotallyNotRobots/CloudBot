import datetime
import logging
from typing import List
from unittest.mock import MagicMock, patch

import freezegun
import pytest
from responses import RequestsMock
from sqlalchemy.orm import close_all_sessions

import cloudbot
from cloudbot.bot import bot
from cloudbot.util import database
from cloudbot.util.database import Session
from tests.util.mock_bot import MockBot
from tests.util.mock_db import MockDB


@pytest.fixture()
def tmp_logs(tmp_path):
    cloudbot._setup(tmp_path)


@pytest.fixture()
def caplog_bot(caplog):
    caplog.set_level(logging.WARNING, "asyncio")
    caplog.set_level(0)
    yield caplog


@pytest.fixture()
def patch_import_module():
    with patch("importlib.import_module") as mocked:
        yield mocked


@pytest.fixture()
def patch_import_reload():
    with patch("importlib.reload") as mocked:
        yield mocked


@pytest.fixture()
def mock_db(tmp_path):
    db = MockDB("sqlite:///" + str(tmp_path / "database.db"))
    database.configure(db.engine)
    yield db
    close_all_sessions()
    Session.remove()
    database.configure()


@pytest.fixture()
def mock_bot_factory(event_loop, tmp_path):
    instances: List[MockBot] = []

    def _factory(*args, **kwargs):
        kwargs.setdefault("loop", event_loop)
        kwargs.setdefault("base_dir", tmp_path)
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
    with freezegun.freeze_time(dt, tz_offset=-5) as ft:
        yield ft


@pytest.fixture()
def mock_api_keys():
    mock_bot = MagicMock()
    try:
        bot.set(mock_bot)
        # pylint: disable=no-member
        mock_bot.config.get_api_key.return_value = "APIKEY"
        yield mock_bot
    finally:
        bot.set(None)


@pytest.fixture()
def unset_bot():
    try:
        yield
    finally:
        bot.set(None)


@pytest.fixture()
def mock_feedparse():
    with patch("feedparser.parse") as mock:
        yield mock
