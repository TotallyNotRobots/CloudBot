import pytest
from mock import patch


@pytest.fixture()
def patch_try_shorten():
    with patch('cloudbot.util.web.try_shorten', lambda x: x):
        yield


@pytest.fixture()
def unset_bot():
    yield
    from cloudbot.bot import bot
    bot.set(None)
