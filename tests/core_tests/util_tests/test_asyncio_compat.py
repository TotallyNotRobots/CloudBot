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


def test_run_coroutine_threadsage(loop):
    from cloudbot.util.compat.asyncio import run_coroutine_threadsafe

    def _run_coro_in_thread():
        run_coroutine_threadsafe(asyncio.sleep(0), loop).result()

    @asyncio.coroutine
    def _coro():
        yield from loop.run_in_executor(None, _run_coro_in_thread)

    loop.run_until_complete(_coro())
