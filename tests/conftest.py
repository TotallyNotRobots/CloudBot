import datetime
from unittest.mock import MagicMock

import freezegun
import pytest

from cloudbot.bot import bot


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
