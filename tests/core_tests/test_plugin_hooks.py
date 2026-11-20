"""
Validates all hook registrations in all plugins
"""

from __future__ import annotations

import importlib
import inspect
import re
import typing
from enum import Enum, auto
from functools import wraps
from numbers import Number
from pathlib import Path
from re import Match
from types import GenericAlias, NoneType, UnionType
from typing import Any, ParamSpec, TypeVar, assert_never, cast, get_type_hints
from unittest.mock import patch

import pytest
import typing_extensions
from irclib.parser import Message, ParamList, TagList
from sqlalchemy.orm import Session

import cloudbot.bot
from cloudbot.bot import AbstractBot, CloudBot
from cloudbot.client import Client
from cloudbot.clients.irc import IrcClient
from cloudbot.event import (
    CapEvent,
    CommandEvent,
    Event,
    EventType,
    IrcOutEvent,
    PostHookEvent,
    RegexEvent,
)
from cloudbot.event_functions import (
    EventAction,
    EventAdminLog,
    EventAsyncCall,
    EventCheckPermission,
    EventCheckPermissions,
    EventCtcp,
    EventHasPermission,
    EventIsNickValid,
    EventMessage,
    EventNotice,
    EventNoticeDoc,
    EventReply,
)
from cloudbot.hook import (
    Action,
    command,
    config,
    event,
    irc_out,
    irc_raw,
    on_cap_ack,
    on_cap_available,
    on_connect,
    on_start,
    on_stop,
    periodic,
    permission,
    post_hook,
    regex,
    sieve,
)
from cloudbot.plugin import Plugin
from cloudbot.plugin_hooks import (
    CommandHook,
    ConfigHook,
    EventHook,
    Hook,
    IrcOutHook,
    OnCapAckHook,
    OnCapAvaliableHook,
    OnConnectHook,
    OnStartHook,
    OnStopHook,
    PeriodicHook,
    PermHook,
    PostHookHook,
    RawHook,
    RegexHook,
    SieveHook,
    hook_name_to_plugin,
)
from cloudbot.util import HOOK_ATTR
from tests.util.mock_bot import MockBot

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from typing_extensions import TypeForm


DOC_RE = re.compile(r"^(?:[<{\[][^-]+?[>}\]][^-]+?)*?-\s.+$")
PLUGINS: list[Plugin] = []

P = ParamSpec("P")
T = TypeVar("T")


def patch_hook(wrapped: Callable[P, T]) -> Callable[P, T]:
    @wraps(wrapped)
    def _func(*args: P.args, **kwargs: P.kwargs) -> T:
        _original_init = Hook.__init__

        def patch_hook_init(self, _type, plugin, func_hook) -> None:
            _original_init(self, _type, plugin, func_hook)
            self.func_hook = func_hook

        with patch.object(Hook, "__init__", new=patch_hook_init):
            return wrapped(*args, **kwargs)

    return _func


def gather_plugins() -> Generator[Path]:
    plugin_dir = Path("plugins")
    path_list = plugin_dir.rglob("[!_]*.py")
    return path_list


@patch_hook
def load_plugin(plugin_path) -> Plugin:
    path = Path(plugin_path)
    file_path = path.resolve()
    file_name = file_path.name
    # Resolve the path relative to the current directory
    plugin_path = file_path.relative_to(Path().resolve())
    title = ".".join(plugin_path.parts[1:]).rsplit(".", 1)[0]

    module_name = f"plugins.{title}"

    plugin_module = importlib.import_module(module_name)

    return Plugin(str(file_path), file_name, title, plugin_module)


def get_plugins() -> list[Plugin]:
    if not PLUGINS:
        bot = MockBot(base_dir=Path().resolve())
        cloudbot.bot.bot_instance.set(cast("CloudBot", bot))
        PLUGINS.extend(map(load_plugin, gather_plugins()))
        cloudbot.bot.bot_instance.set(None)
        bot.close()

    return PLUGINS


def pytest_generate_tests(metafunc) -> None:
    if "plugin" in metafunc.fixturenames:  # pragma: no cover
        plugins = get_plugins()
        metafunc.parametrize(
            "plugin", plugins, ids=[plugin.title for plugin in plugins]
        )
    elif "hook" in metafunc.fixturenames:
        plugins = get_plugins()
        hooks = [
            hook
            for plugin in plugins
            for hook_list in plugin.hooks.values()
            for hook in hook_list
        ]
        metafunc.parametrize(
            "hook",
            hooks,
            ids=[f"{hook.plugin.title}.{hook.function_name}" for hook in hooks],
        )


HOOK_ATTR_TYPES: dict[str, type | tuple[type, ...]] = {
    "permissions": (list, set, frozenset, tuple),
    "single_thread": bool,
    "action": Action,
    "priority": int,
    "auto_help": bool,
    "run_on_cmd": bool,
    "only_no_match": bool,
    "interval": Number,
    "initial_interval": Number,
}


@pytest.mark.parametrize(
    "text", ["- Foo", "<text> - Uses <text>", "[text] - Thing with [text]"]
)
def test_doc_re_matches(text) -> None:
    assert DOC_RE.match(text)


@pytest.mark.parametrize(
    "text",
    ["-- Foo", "<text> -- Uses <text>", "<text - Uses text>", "Foobar", "-Baz"],
)
def test_doc_re_no_match(text) -> None:
    assert not DOC_RE.match(text)


def test_hook_kwargs(hook) -> None:
    assert not hook.func_hook.kwargs, (
        f"Unknown arguments '{hook.func_hook.kwargs}' "
        f"passed during registration of hook '{hook.function_name}'"
    )

    for name, types in HOOK_ATTR_TYPES.items():
        try:
            attr = getattr(hook, name)
        except AttributeError:
            continue
        else:
            assert isinstance(attr, types), (
                f"Unexpected type '{type(attr).__name__}' "
                f"for hook attribute '{name}'"
            )


def test_hook_doc(hook) -> None:
    if hook.type != "command":
        return

    assert hook.doc

    assert DOC_RE.match(hook.doc)
    found_blank = False
    for line in hook.function.__doc__.strip().splitlines():
        stripped = line.strip()
        if stripped.startswith(":"):
            assert found_blank
        elif not stripped:
            found_blank = True


def test_hook_args(hook, mock_bot) -> None:
    re_match = re.match(".", "a")
    assert re_match is not None
    bot = mock_bot
    if hook.type in (
        "irc_raw",
        "perm_check",
        "periodic",
        "on_start",
        "on_stop",
        "event",
        "on_connect",
    ):
        event = Event(bot=bot)
    elif hook.type == "command":
        event = CommandEvent(
            bot=bot, hook=hook, text="", triggered_command="", cmd_prefix="."
        )
    elif hook.type == "regex":
        event = RegexEvent(bot=bot, hook=hook, match=re_match)
    elif hook.type.startswith("on_cap"):
        event = CapEvent(bot=bot, cap="")
    elif hook.type == "post_hook":
        event = PostHookEvent(bot=bot)
    elif hook.type == "irc_out":
        event = IrcOutEvent(bot=bot)
    elif hook.type == "sieve":
        return
    else:  # pragma: no cover
        assert False, f"Unhandled hook type '{hook.type}' in tests"

    for arg in hook.required_args:
        has = hasattr(event, arg)
        assert has, f"Undefined parameter '{arg}' for hook function"


EXPECTED_ANNOTATIONS: dict[str, TypeForm[Any]] = {
    "async_call": EventAsyncCall,
    "text": str,
    "is_nick_valid": EventIsNickValid,
    "notice": EventNotice,
    "admin_log": EventAdminLog,
    "check_permission": EventCheckPermission,
    "check_permissions": EventCheckPermissions,
    "has_permission": EventHasPermission,
    "ctcp": EventCtcp,
    "notice_doc": EventNoticeDoc,
    "nick": str,
    "chan": str,
    "bot": CloudBot,
    "match": Match[str],
    "parsed_line": Message,
    "db": Session,
    "irc_paramlist": ParamList,
    "irc_tags": TagList,
    "action": EventAction,
    "message": EventMessage,
    "reply": EventReply,
    "triggered_prefix": str,
}


class AnnotationType(Enum):
    PARAM = auto()
    RETURN = auto()


def _check_type_match(
    type_: TypeForm[Any] | UnionType | None,
    spec_: TypeForm[Any] | UnionType | None,
) -> bool:
    if type_ is None:
        type_ = NoneType
    if spec_ is None:
        spec_ = NoneType
    if type_ == spec_:
        return True
    type_origin = type_
    type_args = None
    if isinstance(type_, GenericAlias):
        type_origin = typing_extensions.get_origin(type_)
        type_args = typing_extensions.get_args(type_)

    spec_origin = spec_
    spec_args: tuple[Any, ...] | None = None
    if isinstance(spec_, GenericAlias):
        spec_origin = typing_extensions.get_origin(spec_)
        spec_args = typing.get_args(spec_)

    if (
        isinstance(type_origin, type)
        and isinstance(spec_origin, type | UnionType)
        and issubclass(type_origin, spec_origin)
        and type_args == spec_args
    ):
        return True

    return False


def _is_union_subset(sub: UnionType, union: UnionType) -> bool:
    return all(
        any(_check_type_match(s, u) for u in typing.get_args(union))
        for s in typing.get_args(sub)
    )


def _match_annotation(
    actual: TypeForm[Any] | UnionType,
    expected: TypeForm[Any] | UnionType,
    annotation_type: AnnotationType,
) -> bool:
    if annotation_type is AnnotationType.PARAM:
        if isinstance(actual, UnionType):
            if any(
                _match_annotation(item, expected, annotation_type)
                for item in typing.get_args(actual)
            ):
                return True

        if _check_type_match(expected, actual):
            return True
    elif annotation_type is AnnotationType.RETURN:
        if isinstance(expected, UnionType):
            if isinstance(actual, UnionType) and _is_union_subset(
                actual, expected
            ):
                return True
            if any(
                _match_annotation(actual, item, annotation_type)
                for item in typing.get_args(expected)
            ):
                return True

        if _check_type_match(actual, expected):
            return True
    else:
        assert_never(annotation_type)

    return False


def _get_return_type(hook: Hook) -> TypeForm[Any] | UnionType | None:
    if hook.type in ("command", "regex"):
        return str | list[str] | tuple[str] | None

    if hook.type == "irc_out":
        return str | Message | None

    if hook.type in ("on_cap_available", "perm_check"):
        return bool | None

    return None


def _get_event_type(hook: Hook):
    if hook.type == "command":
        return CommandEvent

    if hook.type in ("on_cap_available", "on_cap_ack"):
        return CapEvent

    return Event


def _get_client_type(hook: Hook):
    if hook.type in ("irc_raw", "irc_out", "on_cap_available", "on_cap_ack"):
        return IrcClient

    if hook.clients and "irc" in hook.clients:
        return IrcClient

    return Client


def build_resolution_map(*targets: type) -> dict[str, type]:
    return {t.__name__: t for t in targets}


_forward_refs = build_resolution_map(
    AbstractBot,
    Client,
    CloudBot,
    CommandEvent,
    Event,
    EventAction,
    EventAdminLog,
    EventAsyncCall,
    EventCtcp,
    EventHasPermission,
    EventIsNickValid,
    EventMessage,
    EventNotice,
    EventNoticeDoc,
    EventReply,
    IrcClient,
    Match,
    Message,
    ParamList,
    Session,
    TagList,
)


def test_hook_annotations(hook: Hook) -> None:
    if hook.type == "sieve":
        return

    event_type = _get_event_type(hook)
    client_type = _get_client_type(hook)
    return_type = _get_return_type(hook)
    annotations = get_type_hints(hook.function, _forward_refs, _forward_refs)
    expected: dict[str, TypeForm[Any] | UnionType | None] = {
        "return": return_type,
        "conn": client_type,
        "event": event_type,
    } | EXPECTED_ANNOTATIONS

    # sig = inspect.signature(hook.function)
    # for param in sig.parameters:
    #     if param in expected:
    #         assert param in annotations, (
    #             f"Missing annotation for {param}, should match {expected[param]}"
    #         )
    # assert "return" in annotations, "Missing return type annotation"
    for k, v in annotations.items():
        # if k == 'return':
        # continue
        # if k not in expected:
        #     continue
        assert k in expected, f"Unexpected parameter {k}"
        assert _match_annotation(
            v,
            expected[k],
            AnnotationType.RETURN if k == "return" else AnnotationType.PARAM,
        ), (
            f"Unexpected annotation {v} ({type(v)}) for {k}, expected {expected[k]} {type(expected[k])}"
        )


def test_coroutine_hooks(hook) -> None:
    if inspect.isgeneratorfunction(hook.function):  # pragma: no cover
        assert inspect.iscoroutinefunction(hook.function), (
            "Non-coroutine generator function used for a hook. This is most likely due to incorrect ordering of the "
            "hook/coroutine decorators."
        )


class MockModule:
    pass


def make_plugin() -> Plugin:
    plugin_dir = Path("plugins").resolve()
    file_path = plugin_dir / "test.py"
    file_name = file_path.name
    return Plugin(str(file_path), file_name, "test", MockModule())


def get_and_wrap_hook(
    func: Callable[..., Any], hook_type: str
) -> (
    CommandHook
    | ConfigHook
    | EventHook
    | IrcOutHook
    | OnCapAckHook
    | OnCapAvaliableHook
    | OnConnectHook
    | OnStartHook
    | OnStopHook
    | PeriodicHook
    | PermHook
    | PostHookHook
    | RawHook
    | RegexHook
    | SieveHook
):
    func_hook = getattr(func, HOOK_ATTR)[hook_type]
    plugin = make_plugin()

    _hook = hook_name_to_plugin(hook_type)(plugin, func_hook)
    return _hook


def test_hook_kwargs_warning() -> None:
    @irc_raw("*", a=1)
    def hook_func() -> None:
        pass  # pragma: no cover

    with patch("cloudbot.plugin_hooks.logger") as mocked_logger:
        get_and_wrap_hook(hook_func, "irc_raw")
        mocked_logger.warning.assert_called_once_with(
            "Ignoring extra args %s from %s", {"a": 1}, "test:hook_func"
        )


def test_hook_catch_all() -> None:
    @irc_raw("*")
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "irc_raw")
    assert _hook.is_catch_all()


def test_cmd_hook_str() -> None:
    @command("test")
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "command")

    assert str(_hook) == "command test from test.py"


def test_re_hook_str() -> None:
    @regex("test")
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "regex")

    assert str(_hook) == "regex hook_func from test.py"


def test_periodic_hook_str() -> None:
    @periodic(5)
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "periodic")

    assert str(_hook) == "periodic hook (5 seconds) hook_func from test.py"


def test_raw_hook_str() -> None:
    @irc_raw("PRIVMSG")
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "irc_raw")

    assert str(_hook) == "irc raw hook_func (PRIVMSG) from test.py"


def test_sieve_hook_str() -> None:
    @sieve()
    def hook_func(a: Any, b: Any, c: Any) -> None:  # pyright: ignore[reportAny, reportUnusedParameter] # Mock function, params are necessary to match usage
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "sieve")

    assert str(_hook) == "sieve hook_func from test.py"


def test_event_hook_str() -> None:
    @event(EventType.message)
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "event")

    assert str(_hook) == "event hook_func (EventType.message) from test.py"


def test_config_hook() -> None:
    @config()
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "config")

    assert str(_hook) == "Config hook hook_func from test.py"


def test_on_start_hook_str() -> None:
    @on_start()
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "on_start")

    assert str(_hook) == "on_start hook_func from test.py"


def test_on_stop_hook_str() -> None:
    @on_stop()
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "on_stop")

    assert str(_hook) == "on_stop hook_func from test.py"


def test_cap_avail_hook_str() -> None:
    @on_cap_available("test-cap")
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "on_cap_available")

    assert str(_hook) == "on_cap_available hook_func from test.py"


def test_cap_ack_hook_str() -> None:
    @on_cap_ack("test-cap")
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "on_cap_ack")

    assert str(_hook) == "on_cap_ack hook_func from test.py"


def test_connect_hook_str() -> None:
    @on_connect()
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "on_connect")

    assert str(_hook) == "on_connect hook_func from test.py"


def test_irc_out_hook_str() -> None:
    @irc_out()
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "irc_out")

    assert str(_hook) == "irc_out hook_func from test.py"


def test_post_hook_hook_str() -> None:
    @post_hook()
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "post_hook")

    assert str(_hook) == "post_hook hook_func from test.py"


def test_perm_hook_str() -> None:
    @permission()
    def hook_func() -> None:
        pass  # pragma: no cover

    _hook = get_and_wrap_hook(hook_func, "perm_check")

    assert str(_hook) == "perm hook hook_func from test.py"
