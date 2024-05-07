import re

import pytest

from cloudbot import hook
from cloudbot.event import EventType
from cloudbot.util import HOOK_ATTR


def _get_hook(func, name):
    return getattr(func, HOOK_ATTR)[name]


@pytest.mark.parametrize(
    "func,name",
    [
        (hook.command, "command"),
        (hook.post_hook, "post_hook"),
        (hook.on_start, "on_start"),
        (hook.connect, "on_connect"),
        (hook.on_connect, "on_connect"),
        (hook.onload, "on_start"),
        (hook.on_unload, "on_stop"),
        (hook.on_stop, "on_stop"),
        (hook.irc_out, "irc_out"),
    ],
)
def test_deprecated_hooks(func, name):
    with pytest.deprecated_call():

        @func
        def f():
            raise NotImplementedError

        assert _get_hook(f, name).function is f


def test_sieve_deprecated_bare():
    with pytest.deprecated_call():

        @hook.sieve
        def f(_bot, _event, _hook):
            raise NotImplementedError

        assert _get_hook(f, "sieve").function is f


def test_hook_decorate():
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
    def f():
        raise NotImplementedError

    assert getattr(f, HOOK_ATTR)["event"].types == {
        EventType.message,
        EventType.notice,
        EventType.action,
    }
    assert getattr(f, HOOK_ATTR)["command"].aliases == {"test"}
    assert getattr(f, HOOK_ATTR)["irc_raw"].triggers == {"*", "PRIVMSG"}

    assert "irc_out" in getattr(f, HOOK_ATTR)
    assert "on_start" in getattr(f, HOOK_ATTR)
    assert "on_stop" in getattr(f, HOOK_ATTR)
    assert "regex" in getattr(f, HOOK_ATTR)
    assert "periodic" in getattr(f, HOOK_ATTR)
    assert "perm_check" in getattr(f, HOOK_ATTR)
    assert "post_hook" in getattr(f, HOOK_ATTR)
    assert "on_connect" in getattr(f, HOOK_ATTR)
    assert "on_cap_available" in getattr(f, HOOK_ATTR)
    assert "on_cap_ack" in getattr(f, HOOK_ATTR)

    assert len(getattr(f, HOOK_ATTR)["regex"].regexes) == 4
    assert getattr(f, HOOK_ATTR)["periodic"].interval == 20

    with pytest.raises(ValueError, match="Invalid command name test 123"):
        hook.command("test 123")(f)

    with pytest.raises(TypeError):
        hook.periodic(f)

    with pytest.raises(TypeError):
        hook.regex(f)

    with pytest.raises(TypeError):
        hook.event(f)

    with pytest.raises(TypeError):
        hook.irc_raw(f)

    @hook.sieve()
    def sieve_func(_bot, _event, _hook):
        raise NotImplementedError

    assert "sieve" in getattr(sieve_func, HOOK_ATTR)

    @hook.sieve()
    def sieve_func2(_bot, _event, _hook):
        raise NotImplementedError

    assert "sieve" in getattr(sieve_func2, HOOK_ATTR)

    @hook.on_connect()
    @hook.irc_out()
    @hook.post_hook()
    @hook.on_start()
    @hook.on_stop()
    def plain_dec(_bot, _event, _hook):
        raise NotImplementedError

    assert sorted(getattr(plain_dec, HOOK_ATTR).keys()) == [
        "irc_out",
        "on_connect",
        "on_start",
        "on_stop",
        "post_hook",
    ]


def test_command_hook_doc():
    @hook.command()
    def test(bot):
        """<arg> - foo
        bar
        baz

        foo"""

    cmd_hook = getattr(test, HOOK_ATTR)["command"]
    assert cmd_hook.doc == "<arg> - foo bar baz"

    @hook.command()
    def test1(bot):
        """<arg> - foo bar baz

        foo"""

    cmd_hook = getattr(test1, HOOK_ATTR)["command"]
    assert cmd_hook.doc == "<arg> - foo bar baz"

    @hook.command()
    def test2(bot):
        """<arg> - foo bar baz"""

    cmd_hook = getattr(test2, HOOK_ATTR)["command"]
    assert cmd_hook.doc == "<arg> - foo bar baz"

    @hook.command()
    def test3(bot):
        """
        <arg> - foo bar baz
        """

    cmd_hook = getattr(test3, HOOK_ATTR)["command"]
    assert cmd_hook.doc == "<arg> - foo bar baz"

    @hook.command()
    def test4(bot):
        """<arg> - foo bar baz"""

    cmd_hook = getattr(test4, HOOK_ATTR)["command"]
    assert cmd_hook.doc == "<arg> - foo bar baz"
