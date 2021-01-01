from unittest.mock import patch

import pytest


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
