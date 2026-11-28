"""
Wraps various asyncio functions
"""

from __future__ import annotations

import asyncio
import inspect
from asyncio import AbstractEventLoop
from typing import TYPE_CHECKING, Any, TypeVar

from typing_extensions import ParamSpec

from cloudbot.util.func_utils import call_with_args

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Mapping
    from concurrent.futures import Executor

    from typing_extensions import TypeIs

_P = ParamSpec("_P")
_T = TypeVar("_T")


def iscoroutinefunction(
    func: Callable[_P, Coroutine[Any, Any, _T]] | Callable[_P, _T],
) -> TypeIs[Callable[_P, Coroutine[Any, Any, _T]]]:
    return inspect.iscoroutinefunction(func)


async def run_func_with_args(
    loop: AbstractEventLoop,
    func: Callable[..., Coroutine[Any, Any, _T]] | Callable[..., _T],
    arg_data: Mapping[str, Any],
    executor: Executor | None = None,
) -> _T:
    if asyncio.iscoroutine(func):
        raise TypeError(
            "A coroutine function or a normal, non-async callable are required"
        )

    if iscoroutinefunction(func):
        return await call_with_args(func, arg_data)

    return await loop.run_in_executor(executor, call_with_args, func, arg_data)
