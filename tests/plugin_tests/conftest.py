import datetime as _dt

import pytest
from mock import patch
from responses import RequestsMock
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


@pytest.fixture()
def mock_requests():
    with RequestsMock() as reqs:
        yield reqs


class MockDB:
    def __init__(self):
        self.engine = create_engine('sqlite:///:memory:')
        self.session = scoped_session(sessionmaker(self.engine))


@pytest.fixture()
def mock_db():
    return MockDB()


@pytest.fixture
def patch_paste():
    with patch('cloudbot.util.web.paste') as mock:
        yield mock


@pytest.fixture()
def patch_try_shorten():
    with patch('cloudbot.util.web.try_shorten', new=lambda x: x):
        yield


@pytest.fixture()
def unset_bot():
    yield
    from cloudbot.bot import bot
    bot.set(None)


class FrozenDatetime(_dt.datetime):
    _now = None

    @classmethod
    def now(cls, *args, **kwargs):
        if cls._now is None:
            return super().now(*args, **kwargs)

        return cls._now


@pytest.fixture()
def freeze_time():
    import time
    now = time.time()
    dt_now = _dt.datetime.fromtimestamp(now)
    with patch('time.time') as mocked, patch('datetime.datetime', new=FrozenDatetime):
        _dt.datetime._now = dt_now
        mocked.return_value = now
