from unittest.mock import MagicMock, call, patch

import pytest
from irclib.parser import Message

from cloudbot import hook
from cloudbot.event import Event, IrcOutEvent
from tests.util.mock_module import MockModule


def test_event_copy():
    event = Event(
        bot=object(),
        conn=object(),
        hook=object(),
        event_type=object(),
        channel=object(),
        nick=object(),
        user=object(),
        host=object(),
    )

    new_event = Event(base_event=event)

    assert event.bot is new_event.bot
    assert event.conn is new_event.conn
    assert event.hook is new_event.hook
    assert event.nick is new_event.nick
    assert len(event) == 20
    assert len(new_event) == len(event)


def test_event_message_no_rarget():
    conn = MagicMock()
    event = Event(conn=conn)
    with pytest.raises(ValueError):
        event.message("foobar")

    assert conn.mock_calls == []


def test_event_reply_no_rarget():
    conn = MagicMock(config={})
    event = Event(
        conn=conn,
    )
    with pytest.raises(ValueError):
        event.reply("foobar")

    assert conn.mock_calls == []


def test_event_action_no_rarget():
    conn = MagicMock(config={})
    event = Event(
        conn=conn,
    )
    with pytest.raises(ValueError):
        event.action("foobar")

    assert conn.mock_calls == []


def test_event_ctcp_no_rarget():
    conn = MagicMock(config={})
    event = Event(
        conn=conn,
    )
    with pytest.raises(ValueError):
        event.ctcp("foobar", "PING")

    assert conn.mock_calls == []


@pytest.mark.asyncio()
async def test_check_permission(mock_bot, caplog_bot):
    conn = MagicMock(config={})
    event = Event(
        conn=conn,
        mask="n!u@h",
        bot=mock_bot,
    )
    conn.permissions.has_perm_mask.return_value = True
    res = await event.check_permission("foo")
    assert res is True
    assert conn.mock_calls == [
        call.permissions.has_perm_mask("n!u@h", "foo", notice=True)
    ]


@pytest.mark.asyncio()
async def test_check_permission_no_hooks(mock_bot, caplog_bot):
    conn = MagicMock(config={})
    event = Event(
        conn=conn,
        mask="n!u@h",
        bot=mock_bot,
    )
    conn.permissions.has_perm_mask.return_value = False
    res = await event.check_permission("foo")
    assert res is False
    assert conn.mock_calls == [
        call.permissions.has_perm_mask("n!u@h", "foo", notice=True)
    ]


@pytest.mark.asyncio()
async def test_check_permission_hooks(
    mock_bot, caplog_bot, patch_import_module
):
    conn = MagicMock(config={})
    event = Event(
        conn=conn,
        mask="n!u@h",
        bot=mock_bot,
    )

    @hook.permission("foo")
    def foo_perm():
        return True

    mod = MockModule()

    mod.foo_perm = foo_perm  # type: ignore[attr-defined]
    patch_import_module.return_value = mod

    await mock_bot.plugin_manager.load_plugin(
        mock_bot.base_dir / "plugins" / "test.py"
    )

    conn.permissions.has_perm_mask.return_value = False
    res = await event.check_permission("foo")
    assert res is True
    assert conn.mock_calls == [
        call.permissions.has_perm_mask("n!u@h", "foo", notice=True)
    ]


def test_event_notice_with_rarget():
    conn = MagicMock(config={})
    event = Event(
        conn=conn,
    )
    event.notice("foobar", target="foo")

    assert conn.mock_calls == [call.notice("foo", "foobar")]


def test_event_notice_no_rarget():
    conn = MagicMock(config={})
    event = Event(
        conn=conn,
    )
    with pytest.raises(ValueError):
        event.notice("foobar")

    assert conn.mock_calls == []


@pytest.mark.parametrize(
    "reply_ping,messages,chan,nick,target,calls",
    [
        [True, [], "#foo", "bar", None, []],
        [
            True,
            ["test"],
            "#foo",
            "bar",
            None,
            [call.message("#foo", "(bar) test")],
        ],
        [False, ["test"], "#foo", "bar", None, [call.message("#foo", "test")]],
        [True, ["test"], "bar", "bar", None, [call.message("bar", "test")]],
        [
            True,
            ["test"],
            "bar",
            "bar",
            "baz",
            [call.message("baz", "(bar) test")],
        ],
    ],
)
def test_reply(reply_ping, messages, chan, nick, target, calls):
    conn = MagicMock(config={"reply_ping": reply_ping})
    event = Event(
        channel=chan,
        conn=conn,
        nick=nick,
    )
    event.reply(*messages, target=target)
    assert conn.mock_calls == calls


def test_event_message():
    conn = MagicMock()
    event = Event(channel="#foo", conn=conn)
    event.message("foobar")
    assert conn.mock_calls == [call.message("#foo", "foobar")]


def test_irc_out_prepare_threaded():
    _hook = MagicMock(required_args=["parsed_line"])
    event = IrcOutEvent(hook=_hook, irc_raw=Message(None, None, "PING", "foo"))
    event.prepare_threaded()
    assert event.parsed_line == "PING foo"


def test_irc_out_prepare_error_threaded():
    _hook = MagicMock(required_args=["parsed_line"])
    event = IrcOutEvent(hook=_hook, irc_raw="@")
    with patch("cloudbot.event.Message.parse") as mocked:
        mocked.side_effect = ValueError()
        event.prepare_threaded()

    assert event.parsed_line is None


@pytest.mark.asyncio()
async def test_irc_out_prepare():
    _hook = MagicMock(required_args=["parsed_line"])
    event = IrcOutEvent(hook=_hook, irc_raw=Message(None, None, "PING", "foo"))
    await event.prepare()
    assert event.parsed_line == "PING foo"


@pytest.mark.asyncio()
async def test_irc_out_prepare_error():
    _hook = MagicMock(required_args=["parsed_line"])
    event = IrcOutEvent(hook=_hook, irc_raw="@")
    with patch("cloudbot.event.Message.parse") as mocked:
        mocked.side_effect = ValueError()
        await event.prepare()

    assert event.parsed_line is None
