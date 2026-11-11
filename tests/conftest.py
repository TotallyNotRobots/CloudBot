from __future__ import annotations

import asyncio
import datetime as dt
import importlib
import logging
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import freezegun
import pytest
import pytest_asyncio
from responses import RequestsMock
from sqlalchemy import orm as sa_orm
from sqlalchemy.orm import close_all_sessions

import cloudbot
from cloudbot.bot import bot_instance
from cloudbot.util import database
from cloudbot.util.database import Session
from tests.util.mock_bot import MockBot
from tests.util.mock_db import MockDB

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture()
def temp_metadata():
    new_base = sa_orm.declarative_base()
    with (
        patch("cloudbot.util.database.Base", new=new_base),
        patch("cloudbot.util.database.base", new=new_base),
        patch("cloudbot.util.database.metadata", new=new_base.metadata),
    ):
        yield


@pytest.fixture()
def tmp_logs(tmp_path) -> None:
    cloudbot._setup(tmp_path)


@pytest.fixture()
def caplog_bot(
    caplog: pytest.LogCaptureFixture,
) -> Generator[pytest.LogCaptureFixture]:
    caplog.set_level(logging.WARNING, "asyncio")
    caplog.set_level(logging.WARNING, "alembic")
    caplog.set_level(0, "cloudbot")
    caplog.set_level(0, "plugins")
    caplog.set_level(0)
    logging.getLogger("cloudbot").propagate = True
    yield caplog


@pytest.fixture()
def patch_import_module():
    with patch.object(importlib, "import_module") as mocked:
        yield mocked


@pytest.fixture()
def patch_import_reload():
    with patch.object(importlib, "reload") as mocked:
        yield mocked


@pytest.fixture()
def mock_db(tmp_path):
    db = MockDB(f"sqlite:///{tmp_path / 'database.db'!s}")
    database.configure(db.engine)
    try:
        yield db
    finally:
        close_all_sessions()
        Session.remove()
        database.configure()
        db.close()


@pytest.fixture()
def mock_bot_factory(tmp_path, unset_bot, mock_db):
    instances: list[MockBot] = []

    def _factory(**kwargs):
        loop = kwargs.get("loop")
        if loop is None:
            loop = asyncio.get_running_loop()

        kwargs["loop"] = loop
        kwargs.setdefault("base_dir", tmp_path)
        kwargs.setdefault("db", mock_db)
        _bot = MockBot(**kwargs)
        bot_instance.set(_bot)
        instances.append(_bot)
        return _bot

    try:
        yield _factory
    finally:
        for b in instances:
            b.close()


@pytest_asyncio.fixture()
async def mock_bot(mock_bot_factory):
    yield mock_bot_factory()


@pytest.fixture()
def mock_requests():
    with RequestsMock() as reqs:
        yield reqs


@pytest.fixture()
def freeze_time():
    # Make sure some randomness in the time doesn't break a test
    ts = dt.datetime(2019, 8, 22, 18, 14, 36)
    with freezegun.freeze_time(ts, tz_offset=-5) as ft:
        yield ft


@pytest.fixture()
def mock_api_keys():
    mock_bot = MagicMock()
    try:
        bot_instance.set(mock_bot)
        mock_bot.config.get_api_key.return_value = "APIKEY"
        yield mock_bot
    finally:
        bot_instance.set(None)


@pytest.fixture()
def unset_bot():
    try:
        yield
    finally:
        bot_instance.set(None)


@pytest.fixture()
def mock_feedparse():
    with patch("feedparser.parse") as mock:
        yield mock
