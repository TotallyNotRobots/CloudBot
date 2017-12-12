"""
Wraps various asyncio functions
"""

import asyncio

import sys
from functools import partial


def wrap_future(fut, *, loop=None):
    """
    Wraps asyncio.async()/asyncio.ensure_future() depending on the python version
    :param fut: The awaitable, future, or coroutine to wrap
    :param loop: The loop to run in
    :return: The wrapped future
    """
    if sys.version_info < (3, 4, 4):
        # This is to avoid a SyntaxError on 3.7.0a2+
        func = getattr(asyncio, "async")
    else:
        func = asyncio.ensure_future

    return func(fut, loop=loop)


@asyncio.coroutine
def run_func(loop, func, *args, **kwargs):
    part = partial(func, *args, **kwargs)
    if asyncio.iscoroutine(func) or asyncio.iscoroutinefunction(func):
        return (yield from part())
    else:
        return (yield from loop.run_in_executor(None, part))


def run_coroutine_threadsafe(coro, loop):
    """
    Runs a coroutine in a threadsafe manner
    :type coro: coroutine
    :type loop: asyncio.AbstractEventLoop
    """
    if not asyncio.iscoroutine(coro):
        raise TypeError('A coroutine object is required')

    if sys.version_info < (3, 5, 1):
        loop.call_soon_threadsafe(partial(wrap_future, coro, loop=loop))
    else:
        asyncio.run_coroutine_threadsafe(coro, loop)
