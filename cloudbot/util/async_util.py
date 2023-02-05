"""
Wraps various asyncio functions
"""

import asyncio
from asyncio import AbstractEventLoop
from asyncio.tasks import Task
from functools import partial
from typing import List, cast

from cloudbot.util.func_utils import call_with_args

try:
    _asyncio_get_tasks = getattr(asyncio, "all_tasks")
except AttributeError:
    _asyncio_get_tasks = getattr(Task, "all_tasks")


def wrap_future(fut, *, loop=None):
    """
    Wraps asyncio.ensure_future()
    :param fut: The awaitable, future, or coroutine to wrap
    :param loop: The loop to run in
    :return: The wrapped future
    """
    return asyncio.ensure_future(fut, loop=loop)


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


def create_future(loop):
    return loop.create_future()


def get_all_tasks(loop: AbstractEventLoop = None) -> List[Task]:
    """
    Get a list of all tasks for the current loop
    """
    return cast(List[Task], _asyncio_get_tasks(loop))
