"""
Wraps various asyncio functions
"""

import asyncio
from functools import partial

from cloudbot.util.func_utils import call_with_args


async def run_func(loop, func, *args, **kwargs):
    part = partial(func, *args, **kwargs)
    if asyncio.iscoroutine(func) or asyncio.iscoroutinefunction(func):
        return await part()

    return await loop.run_in_executor(None, part)


async def run_func_with_args(loop, func, arg_data, executor=None):
    if asyncio.iscoroutine(func):
        raise TypeError(
            "A coroutine function or a normal, non-async callable are required"
        )

    if asyncio.iscoroutinefunction(func):
        coro = call_with_args(func, arg_data)
    else:
        coro = loop.run_in_executor(executor, call_with_args, func, arg_data)

    return await coro


def run_coroutine_threadsafe(coro, loop):
    """
    Runs a coroutine in a threadsafe manner
    """
    if not asyncio.iscoroutine(coro):
        raise TypeError("A coroutine object is required")

    asyncio.run_coroutine_threadsafe(coro, loop)
