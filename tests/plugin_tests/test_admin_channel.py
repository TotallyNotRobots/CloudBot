from unittest.mock import MagicMock, call

import pytest

from cloudbot.event import CommandEvent
from cloudbot.util.irc import ChannelMode, ModeType
from plugins import admin_channel
from plugins.core.server_info import ServerInfo, ServerInfoExt
from tests.util import wrap_hook_response_async
from tests.util.mock_irc_client import MockIrcClient


@pytest.mark.asyncio
async def test_ban_no_char(mock_bot) -> None:
    conn = MockIrcClient(bot=mock_bot)
    event = CommandEvent(
        conn=conn,
        channel="#bar",
        nick="test",
        text="foo",
        cmd_prefix=".",
        triggered_command="ban",
        hook=MagicMock(),
    )
    assert await wrap_hook_response_async(admin_channel.ban, event) == [
        (
            "notice",
            (
                "test",
                "Mode character 'b' does not seem to exist on this network.",
            ),
        ),
    ]
    assert conn.mock_calls() == []


@pytest.mark.asyncio
async def test_ban(mock_bot) -> None:
    conn = MockIrcClient(bot=mock_bot)
    event = CommandEvent(
        conn=conn,
        channel="#bar",
        nick="test",
        text="foo",
        triggered_command="ban",
        cmd_prefix=".",
        hook=MagicMock(),
    )
    ServerInfoExt.set(
        conn,
        ServerInfo(
            channel_modes={
                "b": ChannelMode("b", ModeType.A),
            }
        ),
    )
    assert await wrap_hook_response_async(admin_channel.ban, event) == [
        ("notice", ("test", "Attempting to ban foo in #bar...")),
        ("admin_log", ("test used ban to set +b on foo in #bar.",)),
    ]
    assert conn.mock_calls() == [
        call.send("MODE #bar +b foo"),
    ]


@pytest.mark.asyncio
async def test_ban_other_chan(mock_bot) -> None:
    conn = MockIrcClient(bot=mock_bot)
    event = CommandEvent(
        conn=conn,
        channel="#bar",
        nick="test",
        text="#baz foo",
        triggered_command="ban",
        cmd_prefix=".",
        hook=MagicMock(),
    )
    ServerInfoExt.set(
        conn,
        ServerInfo(
            channel_modes={
                "b": ChannelMode("b", ModeType.A),
            }
        ),
    )
    assert await wrap_hook_response_async(admin_channel.ban, event) == [
        ("notice", ("test", "Attempting to ban foo in #baz...")),
        ("admin_log", ("test used ban to set +b on foo in #baz.",)),
    ]
    assert conn.mock_calls() == [
        call.send("MODE #baz +b foo"),
    ]


@pytest.mark.asyncio
async def test_lock(mock_bot) -> None:
    conn = MockIrcClient(bot=mock_bot)
    event = CommandEvent(
        conn=conn,
        channel="#bar",
        nick="test",
        triggered_command="ban",
        cmd_prefix=".",
        hook=MagicMock(),
        text="",
    )
    ServerInfoExt.set(
        conn,
        ServerInfo(
            channel_modes={
                "i": ChannelMode("i", ModeType.D),
            }
        ),
    )
    assert await wrap_hook_response_async(admin_channel.lock, event) == [
        ("notice", ("test", "Attempting to lock #bar...")),
        ("admin_log", ("test used lock to set +i in #bar.",)),
    ]
    assert conn.mock_calls() == [call.send("MODE #bar +i")]


@pytest.mark.asyncio
async def test_quiet(mock_bot) -> None:
    conn = MockIrcClient(bot=mock_bot, config={})
    event = CommandEvent(
        conn=conn,
        channel="#bar",
        nick="test",
        text="foo",
        triggered_command="ban",
        cmd_prefix=".",
        hook=MagicMock(),
    )
    ServerInfoExt.set(
        conn,
        ServerInfo(
            channel_modes={
                "b": ChannelMode("b", ModeType.A),
            },
            extban_prefix="",
            extbans="m",
        ),
    )

    assert await wrap_hook_response_async(admin_channel.quiet, event) == [
        ("notice", ("test", "Attempting to quiet m:foo in #bar...")),
        ("admin_log", ("test used quiet to set +b on m:foo in #bar.",)),
    ]

    assert conn.mock_calls() == [
        call.send("MODE #bar +b m:foo"),
    ]
