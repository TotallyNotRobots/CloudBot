from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, call

import pytest
from irclib.parser import ParamList

from cloudbot.config import ChannelConfig
from plugins.core import core_misc
from tests.util.mock_bot import MockBotFactory
from tests.util.mock_conn import MockClient
from tests.util.mock_db import MockDB, with_mock_db
from tests.util.mock_irc_client import MockIrcClient

if TYPE_CHECKING:
    from tests.util.mock_bot import MockBotFactory
    from tests.util.mock_db import MockDB


@pytest.mark.asyncio
async def test_do_joins(
    mock_bot_factory: MockBotFactory, mock_db: MockDB
) -> None:
    client = MockClient(
        bot=mock_bot_factory(db=mock_db),
        name="foo",
        nick="foobot",
        channels=[
            "#foo",
            "#bar key",
            ["#baz", "key1"],
            ChannelConfig({"name": "#chan"}),
            ChannelConfig({"name": "#chan1", "key": "key2"}),
        ],
    )

    client.ready = True
    client.config["join_throttle"] = 0

    await core_misc.do_joins(client)

    assert client.mock_calls() == [
        call.join("#foo", None),
        call.join("#bar", "key"),
        call.join("#baz", "key1"),
        call.join("#chan", None),
        call.join("#chan1", "key2"),
    ]


@pytest.mark.asyncio
async def test_invite_join(
    mock_bot_factory: MockBotFactory, mock_db: MockDB
) -> None:
    bot = mock_bot_factory(db=mock_db)
    conn = MockIrcClient(
        bot=bot,
        name="fooconn",
        nick="foo",
        config={"connection": {"server": "host.invalid"}},
    )
    core_misc.invite(ParamList("foo", "#bar"), conn)

    assert conn.mock_calls() == [call.send("JOIN #bar", True)]


@pytest.mark.asyncio
async def test_invite_join_disabled(
    mock_bot_factory: MockBotFactory, mock_db: MockDB
) -> None:
    bot = mock_bot_factory(db=mock_db)
    conn = MockIrcClient(
        bot=bot,
        name="fooconn",
        nick="foo",
        config={"connection": {"server": "host.invalid"}, "invite_join": False},
    )
    core_misc.invite(ParamList("foo", "#bar"), conn)

    assert conn.mock_calls() == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("config", "calls"),
    [
        ({}, []),
        ({"log_channel": "#foo"}, [call.send("JOIN #foo", True)]),
        ({"log_channel": "#foo bar"}, [call.send("JOIN #foo bar", True)]),
        (
            {"log_channel": "#foo bar baz"},
            [call.send("JOIN #foo :bar baz", True)],
        ),
        (
            {"nickserv": {"nickserv_password": "foobar"}},
            [call.send("PRIVMSG nickserv :IDENTIFY foobar", True)],
        ),
        (
            {
                "nickserv": {
                    "nickserv_password": "foobar",
                    "nickserv_user": "foo",
                }
            },
            [call.send("PRIVMSG nickserv :IDENTIFY foo foobar", True)],  # pyright: ignore[reportAny] # TODO: find a better way to match calls
        ),
        (
            {
                "nickserv": {
                    "enabled": False,
                    "nickserv_password": "foobar",
                    "nickserv_user": "foo",
                }
            },
            [],
        ),
        ({"mode": "+I"}, [call.send("MODE foobot +I", True)]),
    ],
)
@with_mock_db()
async def test_on_connect(config, calls) -> None:
    bot = MagicMock()
    config = config.copy()
    config.setdefault("connection", {}).setdefault("server", "host.invalid")
    conn = MockIrcClient(bot=bot, name="fooconn", nick="foobot", config=config)

    res = await core_misc.onjoin(conn, bot)

    assert res is None

    assert conn.mock_calls() == calls
