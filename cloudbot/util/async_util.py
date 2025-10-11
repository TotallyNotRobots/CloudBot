"""
Wraps various asyncio functions
"""

import asyncio
import inspect

from cloudbot.util.func_utils import call_with_args


async def run_func_with_args(loop, func, arg_data, executor=None):
    if asyncio.iscoroutine(func):
        raise TypeError(
            "A coroutine function or a normal, non-async callable are required"
        )

    if inspect.iscoroutinefunction(func):
        coro = call_with_args(func, arg_data)
    else:
        coro = loop.run_in_executor(executor, call_with_args, func, arg_data)

    return await coro
