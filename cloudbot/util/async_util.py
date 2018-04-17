"""
Wraps various asyncio functions
"""

import asyncio as _asyncio

from .compat import asyncio as _asyncio_compat
from .func_utils import call_with_args as _call_with_args

_asyncio_iscoroutine = _asyncio.iscoroutine
_asyncio_iscoroutinefunction = _asyncio.iscoroutinefunction

# Kept for compatibility
wrap_future = _asyncio_compat.ensure_future
run_coroutine_threadsafe = _asyncio_compat.run_coroutine_threadsafe
create_future = _asyncio_compat.create_future


@_asyncio.coroutine
def run_func_with_args(loop, func, arg_data, executor=None):
    if _asyncio_iscoroutine(func):
        raise TypeError('A coroutine function or a normal, non-async callable are required')

    if _asyncio_iscoroutinefunction(func):
        coro = _call_with_args(func, arg_data)
    else:
        coro = loop.run_in_executor(executor, _call_with_args, func, arg_data)

    return (yield from coro)
