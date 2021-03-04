from unittest.mock import MagicMock, call

from cloudbot.event import CommandEvent, Event
from cloudbot.hook import _CommandHook, _Hook
from cloudbot.plugin_hooks import CommandHook, Hook
from plugins.core import core_hooks


def test_autohelp():
    def f():
        """foo"""

    event = Event(
        hook=Hook("foo", None, _Hook(f, "foo")),
    )
    res = core_hooks.cmd_autohelp(event.bot, event, event.hook)
    assert res is event

    cmd_hook = _CommandHook(f)
    cmd_hook.add_hook("foo", {})
    conn = MagicMock(config={})
    event = CommandEvent(
        hook=CommandHook(None, cmd_hook),
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
