import inspect
from collections.abc import Mapping
from pathlib import Path
from unittest.mock import patch

from cloudbot.util.func_utils import call_with_args

__all__ = (
    "HookResult",
    "wrap_hook_response",
    "get_data_file",
)


class HookResult:
    def __init__(self, return_type, value, data=None) -> None:
        self.return_type = return_type
        self.value = value
        self.data = data

    def as_tuple(self):
        if not self.data:
            return self.return_type, self.value

        return (
            self.return_type,
            self.value,
            self.data,
        )

    def __eq__(self, other):
        if isinstance(other, HookResult):
            return self.as_tuple() == other.as_tuple()

        if isinstance(other, (list, tuple)):
            return self == HookResult(*other)

        if isinstance(other, Mapping):
            return self == HookResult(**other)

        return False

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return str(self.as_tuple())


def wrap_hook_response(func, event, results=None):
    """
    Wrap the response from a hook, allowing easy assertion against calls to
    event.notice(), event.reply(), etc instead of just returning a string
    """
    if results is None:
        results = []

    def add_result(name, value, data=None) -> None:
        results.append(HookResult(name, value, data))

    def notice(*args, **kwargs) -> None:  # pragma: no cover
        add_result("notice", args, kwargs)

    def message(*args, **kwargs) -> None:  # pragma: no cover
        add_result("message", args, kwargs)

    def action(*args, **kwargs) -> None:  # pragma: no cover
        add_result("action", args, kwargs)

    def admin_log(*args, **kwargs) -> None:  # pragma: no cover
        add_result("admin_log", args, kwargs)

    patch_notice = patch.object(event.conn, "notice", notice)
    patch_message = patch.object(event.conn, "message", message)
    patch_action = patch.object(event.conn, "action", action)
    patch_admin_log = patch.object(event, "admin_log", admin_log)

    with patch_action, patch_message, patch_notice, patch_admin_log:
        res = call_with_args(func, event)
        if res is not None:
            add_result("return", res)

    return results


async def wrap_hook_response_async(func, event, results=None):
    """
    Wrap the response from a hook, allowing easy assertion against calls to
    event.notice(), event.reply(), etc instead of just returning a string
    """
    if results is None:
        results = []

    async def async_call(func, *args, **kwargs):
        return func(*args, **kwargs)

    def add_result(name, value, data=None) -> None:
        results.append(HookResult(name, value, data))

    def notice(*args, **kwargs) -> None:  # pragma: no cover
        add_result("notice", args, kwargs)

    def message(*args, **kwargs) -> None:  # pragma: no cover
        add_result("message", args, kwargs)

    def action(*args, **kwargs) -> None:  # pragma: no cover
        add_result("action", args, kwargs)

    def admin_log(*args, **kwargs) -> None:  # pragma: no cover
        add_result("admin_log", args, kwargs)

    patch_notice = patch.object(event.conn, "notice", notice)
    patch_message = patch.object(event.conn, "message", message)
    patch_action = patch.object(event.conn, "action", action)
    patch_async_call = patch.object(event, "async_call", async_call)
    patch_admin_log = patch.object(event, "admin_log", admin_log)

    with (
        patch_action,
        patch_message,
        patch_notice,
        patch_async_call,
        patch_admin_log,
    ):
        res = call_with_args(func, event)
        if inspect.isawaitable(res):
            res = await res

        if res is not None:
            add_result("return", res)

    return results


def get_data_path() -> Path:
    return Path(__file__).parent.parent / "data"


def get_data_file(name: str) -> Path:
    return get_data_path() / name
