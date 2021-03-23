from typing import cast
from unittest.mock import MagicMock, call

import pytest
from irclib.parser import ParamList

from plugins.core import core_misc
from tests.util.mock_irc_client import MockIrcClient


def test_invite_join(mock_bot_factory, event_loop):
    bot = mock_bot_factory(loop=event_loop)
    conn = MockIrcClient(
        bot, "fooconn", "foo", {"connection": {"server": "host.invalid"}}
    )
    core_misc.invite(ParamList("foo", "#bar"), conn)

    assert cast(MagicMock, conn.send).mock_calls == [call("JOIN #bar")]


def test_invite_join_disabled(mock_bot_factory, event_loop):
    bot = mock_bot_factory(loop=event_loop)
    conn = MockIrcClient(
        bot,
        "fooconn",
        "foo",
        {"connection": {"server": "host.invalid"}, "invite_join": False},
    )
    core_misc.invite(ParamList("foo", "#bar"), conn)

    assert cast(MagicMock, conn.send).mock_calls == []


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    "config,calls",
    [
        ({}, []),
        ({"log_channel": "#foo"}, [call("JOIN #foo")]),
        ({"log_channel": "#foo bar"}, [call("JOIN #foo bar")]),
        ({"log_channel": "#foo bar baz"}, [call("JOIN #foo :bar baz")]),
        (
            {"nickserv": {"nickserv_password": "foobar"}},
            [call("PRIVMSG nickserv :IDENTIFY foobar")],
        ),
        (
            {
                "nickserv": {
                    "nickserv_password": "foobar",
                    "nickserv_user": "foo",
                }
            },
            [call("PRIVMSG nickserv :IDENTIFY foo foobar")],
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
        ({"mode": "+I"}, [call("MODE foobot +I")]),
    ],
)
async def test_on_connect(config, calls):
    bot = MagicMock()
    config = config.copy()
    config.setdefault("connection", {}).setdefault("server", "host.invalid")
    conn = MockIrcClient(bot, "fooconn", "foobot", config)

    res = await core_misc.onjoin(conn, bot)

    assert res is None

    assert cast(MagicMock, conn.send).mock_calls == calls
