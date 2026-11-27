from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import pytest

from cloudbot import hook
from cloudbot.event import Event, EventType
from cloudbot.hook import (
    CommandFuncHook,
    ConnectFuncHook,
    EventFuncHook,
    FuncHook,
    Hooks,
    HookType,
    IrcOutFuncHook,
    OnStartFuncHook,
    OnStopFuncHook,
    PeriodicFuncHook,
    PostHookFuncHook,
    RawFuncHook,
    RegexFuncHook,
    SieveFuncHook,
    command,
)

if TYPE_CHECKING:
    from cloudbot.bot import CloudBot
    from cloudbot.plugin_hooks import Hook


@pytest.mark.parametrize(
    ("func", "cls"),
    [
        (hook.command, CommandFuncHook),
        (hook.post_hook, PostHookFuncHook),
        (hook.on_start, OnStartFuncHook),
        (hook.connect, ConnectFuncHook),
        (hook.on_connect, ConnectFuncHook),
        (hook.onload, OnStartFuncHook),
        (hook.on_unload, OnStopFuncHook),
        (hook.on_stop, OnStopFuncHook),
        (hook.irc_out, IrcOutFuncHook),
    ],
)
def test_deprecated_hooks(func, cls: type[FuncHook[Any]]) -> None:
    with pytest.deprecated_call():

        @func
        def f():
            raise NotImplementedError

        assert cls.get_hook(f, raise_on_missing=True).function is f


def test_sieve_deprecated_bare() -> None:
    with pytest.deprecated_call():

        @hook.sieve  # pyright: ignore[reportDeprecated]
        def f(_bot: CloudBot, _event: Event, _hook: Hook[Any]) -> None:
            raise NotImplementedError

        assert SieveFuncHook.get_hook(f, raise_on_missing=True).function is f


def test_hook_decorate() -> None:
    @hook.event(EventType.message)
    @hook.event([EventType.notice, EventType.action])
    @hook.command("test")
    @hook.irc_raw("*")
    @hook.irc_raw(["PRIVMSG"])
    @hook.irc_out()
    @hook.on_stop()
    @hook.on_start()
    @hook.regex(["test", re.compile("test")])
    @hook.regex("test1")
    @hook.regex(re.compile("test2"))
    @hook.periodic(20)
    @hook.permission("perm")
    @hook.post_hook()
    @hook.on_connect()
    @hook.on_cap_ack("capname")
    @hook.on_cap_available("capname")
    def f() -> None:
        raise NotImplementedError

    assert EventFuncHook.get_hook(f, raise_on_missing=True).types == {
        EventType.message,
        EventType.notice,
        EventType.action,
    }
    assert CommandFuncHook.get_hook(f, raise_on_missing=True).aliases == {
        "test"
    }
    assert RawFuncHook.get_hook(f, raise_on_missing=True).triggers == {
        "*",
        "PRIVMSG",
    }

    hooks = Hooks.get_from_func(f)
    hook_types = hooks.get_types() if hooks is not None else []
    assert HookType.IRC_OUT in hook_types
    assert HookType.ON_START in hook_types
    assert HookType.ON_STOP in hook_types
    assert HookType.REGEX in hook_types
    assert HookType.PERIODIC in hook_types
    assert HookType.PERMISSION in hook_types
    assert HookType.POST_HOOK in hook_types
    assert HookType.CONNECT in hook_types
    assert HookType.CAP_AVAILABLE in hook_types
    assert HookType.CAP_ACK in hook_types

    assert len(RegexFuncHook.get_hook(f, raise_on_missing=True).regexes) == 4
    assert PeriodicFuncHook.get_hook(f, raise_on_missing=True).interval == 20

    with pytest.raises(ValueError, match="Invalid command name test 123"):
        hook.command("test 123")(f)

    with pytest.raises(TypeError):
        hook.periodic(f)  # pyright: ignore[reportArgumentType]

    with pytest.raises(TypeError):
        hook.regex(f)  # pyright: ignore[reportArgumentType]

    with pytest.raises(TypeError):
        hook.event(f)  # pyright: ignore[reportArgumentType]

    with pytest.raises(TypeError):
        hook.irc_raw(f)  # pyright: ignore[reportArgumentType]

    @hook.sieve()
    def sieve_func(_bot, _event, _hook):
        raise NotImplementedError

    hooks = Hooks.get_from_func(sieve_func)
    assert hooks
    assert HookType.SIEVE in hooks.get_types()

    @hook.sieve()
    def sieve_func2(_bot, _event, _hook):
        raise NotImplementedError

    hooks = Hooks.get_from_func(sieve_func2)
    assert hooks
    assert HookType.SIEVE in hooks.get_types()

    @hook.on_connect()
    @hook.irc_out()
    @hook.post_hook()
    @hook.on_start()
    @hook.on_stop()
    def plain_dec(_bot, _event, _hook):
        raise NotImplementedError

    hooks = Hooks.get_from_func(plain_dec)
    assert hooks
    assert sorted(hooks.get_types()) == [
        HookType.IRC_OUT,
        HookType.CONNECT,
        HookType.ON_START,
        HookType.ON_STOP,
        HookType.POST_HOOK,
    ]


def test_hook_get_hook_raises_on_missing_hook_with_metadata() -> None:
    @command()
    def foo() -> None:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Missing hook"):
        RawFuncHook.get_hook(foo, raise_on_missing=True)


def test_hook_get_hook_raises_on_missing_hook_no_metadata() -> None:
    def foo() -> None:
        raise NotImplementedError

    with pytest.raises(ValueError, match="Missing hook"):
        RawFuncHook.get_hook(foo, raise_on_missing=True)


def test_command_validate() -> None:
    @hook.command()
    def test() -> None:
        pass

    @hook.command("foo")
    def test1() -> None:
        pass

    @hook.command(["foo"])
    def test2() -> None:
        pass


def test_command_hook_doc() -> None:
    @hook.command()
    def test(bot) -> None:
        """<arg> - foo
        bar
        baz

        foo"""

    cmd_hook = CommandFuncHook.get_hook(test, raise_on_missing=True)
    assert cmd_hook.doc == "<arg> - foo bar baz"

    @hook.command()
    def test1(bot) -> None:
        """<arg> - foo bar baz

        foo"""

    cmd_hook = CommandFuncHook.get_hook(test1, raise_on_missing=True)
    assert cmd_hook.doc == "<arg> - foo bar baz"

    @hook.command()
    def test2(bot) -> None:
        """<arg> - foo bar baz"""

    cmd_hook = CommandFuncHook.get_hook(test2, raise_on_missing=True)
    assert cmd_hook.doc == "<arg> - foo bar baz"

    @hook.command()
    def test3(bot) -> None:
        """
        <arg> - foo bar baz
        """

    cmd_hook = CommandFuncHook.get_hook(test3, raise_on_missing=True)
    assert cmd_hook.doc == "<arg> - foo bar baz"

    @hook.command()
    def test4(bot) -> None:
        """<arg> - foo bar baz"""

    cmd_hook = CommandFuncHook.get_hook(test4, raise_on_missing=True)
    assert cmd_hook.doc == "<arg> - foo bar baz"


def test_sieve_hook_args_validate() -> None:
    with pytest.raises(ValueError, match=r".*incorrect argument count.*"):

        @hook.sieve()
        def _() -> None:
            pass
