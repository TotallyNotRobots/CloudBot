from unittest.mock import MagicMock, call

from cloudbot.event import CommandEvent, Event
from cloudbot.hook import CommandFuncHook, RawFuncHook
from cloudbot.plugin import Plugin
from cloudbot.plugin_hooks import CommandHook, RawHook
from plugins.core import core_hooks
from tests.util.mock_module import MockModule


def test_autohelp() -> None:
    def f() -> None:
        """foo"""

    hook = RawHook(Plugin("", "", "", MockModule()), RawFuncHook(f))
    event = Event(hook=hook)
    res = core_hooks.cmd_autohelp(event.bot, event, hook)
    assert res is event

    cmd_hook = CommandFuncHook(f)
    cmd_hook.add_hook("foo", {})
    conn = MagicMock(config={})
    event = CommandEvent(
        hook=CommandHook(Plugin("", "", "", MockModule()), cmd_hook),
        cmd_prefix=".",
        text="",
        triggered_command="foo",
        conn=conn,
        channel="#foo",
        nick="foo",
    )
    res = core_hooks.cmd_autohelp(event.bot, event, event.hook)
    assert res is None
    assert conn.mock_calls == [call.notice("foo", ".foo foo")]
