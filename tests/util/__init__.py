from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from typing_extensions import ParamSpec, TypeVar

from cloudbot.util.func_utils import call_with_args

if TYPE_CHECKING:
    from cloudbot.event import Event

__all__ = ("HookResult", "wrap_hook_response", "get_data_file")


class HookResult:
    def __init__(
        self,
        return_type: str,
        value: tuple[Any, ...] | Any,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.return_type: str = return_type
        self.value: tuple[Any] = value
        self.data: dict[str, Any] | None = data

    def as_tuple(
        self,
    ) -> tuple[str, tuple[Any]] | tuple[str, tuple[Any], dict[str, Any]]:
        if not self.data:
            return self.return_type, self.value

        return (self.return_type, self.value, self.data)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HookResult):
            return self.as_tuple() == other.as_tuple()

        if isinstance(other, (list, tuple)):
            return self == HookResult(
                other[0],  # pyright: ignore[reportUnknownArgumentType] # If comparing against a list or tuple, these types should match
                other[1],  # pyright: ignore[reportUnknownArgumentType] # If comparing against a list or tuple, these types should match
                other[2] if len(other) > 2 else None,  # pyright: ignore[reportUnknownArgumentType] # If comparing against a list or tuple, these types should match
            )

        if isinstance(other, Mapping):
            return self == HookResult(
                other["return_type"],  # pyright: ignore[reportArgumentType] # If comparing against a mapping, these types should match
                other["value"],
                other.get("data"),  # pyright: ignore[reportArgumentType, reportUnknownMemberType] # If comparing against a mapping, these types should match
            )

        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return str(self.as_tuple())


def wrap_hook_response(
    func: Callable[..., Any],
    event: Event,
    results: list[HookResult] | None = None,
) -> list[HookResult]:
    """
    Wrap the response from a hook, allowing easy assertion against calls to
    event.notice(), event.reply(), etc instead of just returning a string
    """
    if results is None:
        results = []

    def add_result(
        name: str,
        value: tuple[Any, ...] | Any,
        data: dict[str, Any] | None = None,
    ) -> None:
        results.append(HookResult(name, value, data))

    def notice(*args: Any, **kwargs: Any) -> None:  # pragma: no cover  # pyright: ignore[reportAny] # Record all potential arguments
        add_result("notice", args, kwargs)

    def message(*args: Any, **kwargs: Any) -> None:  # pragma: no cover  # pyright: ignore[reportAny] # Record all potential arguments
        add_result("message", args, kwargs)

    def action(*args: Any, **kwargs: Any) -> None:  # pragma: no cover  # pyright: ignore[reportAny] # Record all potential arguments
        add_result("action", args, kwargs)

    patch_notice = patch.object(event.conn, "notice", notice)
    patch_message = patch.object(event.conn, "message", message)
    patch_action = patch.object(event.conn, "action", action)

    with patch_action, patch_message, patch_notice:
        res = call_with_args(func, event)  # pyright: ignore[reportAny] # Hook functions can return anything
        if res is not None:
            add_result("return", res)  # pyright: ignore[reportAny] # Hook functions can return anything

    return results


_P = ParamSpec("_P")
_T = TypeVar("_T")


async def wrap_hook_response_async(
    func: Callable[..., Any],
    event: Event,
    results: list[HookResult] | None = None,
) -> list[HookResult]:
    """
    Wrap the response from a hook, allowing easy assertion against calls to
    event.notice(), event.reply(), etc instead of just returning a string
    """
    if results is None:
        results = []

    async def async_call(
        func: Callable[_P, _T], *args: _P.args, **kwargs: _P.kwargs
    ) -> _T:
        return func(*args, **kwargs)

    def add_result(
        name: str, value: tuple[Any], data: dict[str, Any] | None = None
    ) -> None:
        results.append(HookResult(name, value, data))

    def notice(*args: Any, **kwargs: Any) -> None:  # pragma: no cover  # pyright: ignore[reportAny] # Record all potential arguments
        add_result("notice", args, kwargs)

    def message(*args: Any, **kwargs: Any) -> None:  # pragma: no cover  # pyright: ignore[reportAny] # Record all potential arguments
        add_result("message", args, kwargs)

    def action(*args: Any, **kwargs: Any) -> None:  # pragma: no cover  # pyright: ignore[reportAny] # Record all potential arguments
        add_result("action", args, kwargs)

    patch_notice = patch.object(event.conn, "notice", notice)
    patch_message = patch.object(event.conn, "message", message)
    patch_action = patch.object(event.conn, "action", action)
    patch_async_call = patch.object(event, "async_call", async_call)

    with patch_action, patch_message, patch_notice, patch_async_call:
        res = call_with_args(func, event)  # pyright: ignore[reportAny] Hook functions can return anything
        if inspect.isawaitable(res):  # pyright: ignore[reportAny] # Hook functions can return anything
            res = await res

        if res is not None:
            add_result("return", res)  # pyright: ignore[reportAny] # Hook functions can return anything

    return results


def get_data_path() -> Path:
    return Path(__file__).parent.parent / "data"


def get_data_file(name: str) -> Path:
    return get_data_path() / name


def with_frozen_time() -> pytest.MarkDecorator:
    return pytest.mark.usefixtures("freeze_time")


def with_mock_api_keys() -> pytest.MarkDecorator:
    return pytest.mark.usefixtures("mock_api_keys")


def with_temp_logs() -> pytest.MarkDecorator:
    return pytest.mark.usefixtures("tmp_logs")


PatchImportModule = MagicMock
PatchImportReload = MagicMock
