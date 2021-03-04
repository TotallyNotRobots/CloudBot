import time
from unittest.mock import patch

import pytest

from cloudbot.util import tokenbucket


# noinspection PyProtectedMember
def test_bucket_consume():
    bucket = tokenbucket.TokenBucket(10, 5)
    # larger then capacity
    assert bucket.consume(15) is False
    # success
    assert bucket.consume(10) is True
    # check if bucket has no tokens
    assert bucket._tokens == 0
    # bucket is empty from above, should fail
    assert bucket.consume(10) is False


# noinspection PyProtectedMember
def test_bucket_advanced():
    bucket = tokenbucket.TokenBucket(10, 1)
    # tokens start at 10
    assert bucket._tokens == 10
    # empty tokens
    assert bucket.empty() is True
    # check tokens is 0
    assert bucket._tokens == 0
    # refill tokens
    assert bucket.refill() is True
    # check tokens is 10
    assert bucket._tokens == 10


class MockTime:
    def __init__(self, t_get=time.time):
        self.offset = 0
        self.t = None
        self.tg = t_get

    def _get(self):
        if self.t is not None:
            return self.t

        return self.tg()

    def get(self):
        return self._get() + self.offset

    def freeze(self):
        self.t = self._get()

    def unfreeze(self):
        self.t = None

    def sleep(self, n):
        self.offset += n


@pytest.fixture()
def mock_time():
    mocked = MockTime()
    with patch.object(tokenbucket, "time", mocked.get):
        yield mocked


@pytest.fixture()
def freeze_time(mock_time):
    mock_time.freeze()
    try:
        yield mock_time
    finally:
        mock_time.unfreeze()


def test_bucket_regen(freeze_time):
    bucket = tokenbucket.TokenBucket(10, 10)
    # success
    assert bucket.consume(10) is True
    # sleep
    freeze_time.sleep(1)
    # bucket should be full again and this should succeed
    assert bucket.tokens == 10
    assert bucket.consume(10) is True
