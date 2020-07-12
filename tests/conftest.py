import datetime
from unittest.mock import MagicMock

import freezegun
import pytest
from responses import RequestsMock
from sqlalchemy import MetaData

from cloudbot.bot import bot
from cloudbot.util import database


@pytest.fixture()
def freeze_time():
    # Make sure some randomness in the time doesn't break a test
    dt = datetime.datetime(
        2019, 8, 22, 18, 14, 36, tzinfo=datetime.timezone.utc
    )

    with freezegun.freeze_time(dt, tz_offset=1) as ft:
        yield ft


@pytest.fixture()
def mock_api_keys():
    try:
        bot.set(MagicMock())
        bot.config.get_api_key.return_value = "APIKEY"
        yield bot.config.get_api_key
    finally:
        bot.set(None)


@pytest.fixture()
def mock_requests():
    with RequestsMock() as reqs:
        yield reqs


@pytest.fixture()
def unset_bot():
    try:
        yield
    finally:
        bot.set(None)


@pytest.fixture()
def reset_database():
    database.metadata = MetaData()
    database.base = None
    try:
        yield
    finally:
        database.metadata = MetaData()
        database.base = None
