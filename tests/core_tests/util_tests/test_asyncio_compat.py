import asyncio

import pytest


@pytest.fixture(scope="module")
def loop():
    return asyncio.get_event_loop()


def test_isfuture(loop):
    from cloudbot.util.compat.asyncio import create_future, isfuture
    from concurrent.futures import Future
    assert isfuture(create_future(loop))
    assert not isfuture(Future)


def test_ensure_future(loop):
    from cloudbot.util.compat.asyncio import create_future, isfuture, ensure_future

    assert isfuture(ensure_future(create_future(loop), loop=loop))
