"""
Wraps various asyncio functions
"""

import asyncio
import sys
from functools import partial

from cloudbot.util.func_utils import call_with_args


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

    return func(fut, loop=loop)  # pylint: disable=locally-disabled, deprecated-method


@asyncio.coroutine
def run_func(loop, func, *args, **kwargs):
    part = partial(func, *args, **kwargs)
    if asyncio.iscoroutine(func) or asyncio.iscoroutinefunction(func):
        return (yield from part())
    else:
        return (yield from loop.run_in_executor(None, part))


@asyncio.coroutine
def run_func_with_args(loop, func, arg_data, executor=None):
    if asyncio.iscoroutine(func):
        raise TypeError('A coroutine function or a normal, non-async callable are required')

    if asyncio.iscoroutinefunction(func):
        coro = call_with_args(func, arg_data)
    else:
        coro = loop.run_in_executor(executor, call_with_args, func, arg_data)

    return (yield from coro)


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


def create_future(loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    if sys.version_info < (3, 5, 2):
        return asyncio.Future(loop=loop)

    return loop.create_future()
