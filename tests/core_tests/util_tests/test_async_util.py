import asyncio

import pytest


def test_launch_coroutine():
    @asyncio.coroutine
    def _test():
        return 5

    from cloudbot.util.async_util import run_func_with_args
    loop = asyncio.get_event_loop()
    assert loop.run_until_complete(run_func_with_args(loop, _test, {})) == 5


def test_launch_coroutine_obj():
    @asyncio.coroutine
    def _test():
        return 5

    from cloudbot.util.async_util import run_func_with_args
    loop = asyncio.get_event_loop()
    with pytest.raises(TypeError):
        loop.run_until_complete(run_func_with_args(loop, _test(), {}))


def test_thread_launch():
    def _test():
        return 5

    from cloudbot.util.async_util import run_func_with_args
    loop = asyncio.get_event_loop()
    assert loop.run_until_complete(run_func_with_args(loop, _test, {})) == 5
