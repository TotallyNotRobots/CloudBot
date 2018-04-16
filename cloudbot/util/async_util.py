"""
Wraps various asyncio functions
"""

import asyncio as _asyncio

from .compat import asyncio as _asyncio_compat
from .func_utils import call_with_args as _call_with_args

_asyncio_isfuture = _asyncio.isfuture
_asyncio_iscoroutine = _asyncio.iscoroutine
_asyncio_iscoroutinefunction = _asyncio.iscoroutinefunction

_asyncio_get_event_loop = _asyncio.get_event_loop
_asyncio_future_init = _asyncio.Future

# Kept for compatibility
wrap_future = _asyncio_compat.ensure_future
run_coroutine_threadsafe = _asyncio_compat.run_coroutine_threadsafe


@_asyncio.coroutine
def run_func_with_args(loop, func, arg_data, executor=None):
    if _asyncio_iscoroutine(func):
        raise TypeError('A coroutine function or a normal, non-async callable are required')

    if _asyncio_iscoroutinefunction(func):
        coro = _call_with_args(func, arg_data)
    else:
        coro = loop.run_in_executor(executor, _call_with_args, func, arg_data)

    return (yield from coro)


def create_future(loop=None):
    if loop is None:
        loop = _asyncio_get_event_loop()

    try:
        f = loop.create_future
    except AttributeError:
        return _asyncio_future_init(loop=loop)
    else:
        return f()
