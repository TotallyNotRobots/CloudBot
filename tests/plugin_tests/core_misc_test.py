from unittest.mock import call

from irclib.parser import ParamList

from plugins.core import core_misc
from tests.util.mock_bot import MockBot
from tests.util.mock_irc_client import MockIrcClient


def test_invite_join():
    bot = MockBot({})
    conn = MockIrcClient(
        bot, "fooconn", "foo", {"connection": {"server": "host.invalid"}}
    )
    core_misc.invite(ParamList("foo", "#bar"), conn)

    assert conn.send.mock_calls == [call("JOIN #bar")]


def test_invite_join_disabled():
    bot = MockBot({})
    conn = MockIrcClient(
        bot,
        "fooconn",
        "foo",
        {"connection": {"server": "host.invalid"}, "invite_join": False},
    )
    core_misc.invite(ParamList("foo", "#bar"), conn)

    assert conn.send.mock_calls == []
