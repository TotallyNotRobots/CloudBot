from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from cloudbot.util import tokenbucket

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


def test_bucket_consume() -> None:
    bucket = tokenbucket.TokenBucket(10, 5)
    # larger then capacity
    assert bucket.consume(15) is False
    # success
    assert bucket.consume(10) is True
    # check if bucket has no tokens
    assert bucket._tokens == 0
    # bucket is empty from above, should fail
    assert bucket.consume(10) is False


def test_bucket_advanced() -> None:
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
    def __init__(self, t_get: Callable[[], float] = time.time) -> None:
        self.offset: float = 0
        self.t: float | None = None
        self.tg: Callable[[], float] = t_get

    def _get(self) -> float:
        if self.t is not None:
            return self.t

        return self.tg()

    def get(self) -> float:
        return self._get() + self.offset

    def freeze(self) -> None:
        self.t = self._get()

    def unfreeze(self) -> None:
        self.t = None

    def sleep(self, n: float) -> None:
        self.offset += n


@pytest.fixture()
def mock_time() -> Generator[MockTime]:
    mocked = MockTime()
    with patch.object(tokenbucket, "time", mocked.get):
        yield mocked


@pytest.fixture()
def freeze_time(mock_time: MockTime) -> Generator[MockTime]:
    mock_time.freeze()
    try:
        yield mock_time
    finally:
        mock_time.unfreeze()


def test_bucket_regen(freeze_time) -> None:
    bucket = tokenbucket.TokenBucket(10, 10)
    # success
    assert bucket.consume(10) is True
    # sleep
    freeze_time.sleep(1)
    # bucket should be full again and this should succeed
    assert bucket.tokens == 10
    assert bucket.consume(10) is True
