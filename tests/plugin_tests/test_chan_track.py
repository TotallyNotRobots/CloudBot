from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from irclib.parser import Prefix, TagList

from cloudbot.clients.irc import _IrcProtocol
from cloudbot.util.func_utils import call_with_args
from plugins.core import chan_track, server_info


class MockConn:
    def __init__(self, bot=None, loop=None):
        self.name = "foo"
        self.memory: Dict[str, Any] = {
            "server_info": {
                "statuses": {},
            },
            "server_caps": {
                "userhost-in-names": True,
                "multi-prefix": True,
            },
        }
        self.nick = "BotFoo"
        self.bot = bot
        if self.bot:
            self.loop = self.bot.loop
        else:
            self.loop = loop

    def get_statuses(self, chars):
        return [self.memory["server_info"]["statuses"][c] for c in chars]


def test_replace_user_data(event_loop):
    conn = MockConn(loop=event_loop)
    serv_info = conn.memory["server_info"]
    server_info.handle_prefixes("(YohvV)!@%+-", serv_info)
    users = chan_track.UsersDict(conn)
    conn.memory["users"] = users

    chan = chan_track.Channel("#test", conn)
    chan.data["new_users"] = [
        "@+foo!bar@baz",
        "@ExampleUser!bar@baz",
        "ExampleUser2!bar@baz",
        "!@%+-foo1!bar@baz",
    ]
    chan_track.replace_user_data(conn, chan)

    assert chan.users["foo"].user.mask == Prefix("foo", "bar", "baz")
    assert chan.users["foo1"].user.mask == Prefix("foo1", "bar", "baz")
    assert chan.users["exampleuser"].user.mask == Prefix(
        "ExampleUser", "bar", "baz"
    )
    assert chan.users["exampleuser2"].user.mask == Prefix(
        "ExampleUser2", "bar", "baz"
    )

    assert chan.users["foo"].status == conn.get_statuses("@+")
    assert chan.users["exampleuser"].status == conn.get_statuses("@")
    assert chan.users["Foo1"].status == conn.get_statuses("!@%+-")
    assert not chan.users["exampleuser2"].status


def test_missing_on_nick(event_loop):
    conn = MockConn(loop=event_loop)
    chans = chan_track.get_chans(conn)
    chan = chans.getchan("#foo")

    with pytest.raises(chan_track.MemberNotFoundException):
        chan.users.pop("exampleuser3")


def test_channel_members(event_loop):
    conn = MockConn(loop=event_loop)
    serv_info = conn.memory["server_info"]
    server_info.handle_prefixes("(YohvV)!@%+-", serv_info)
    server_info.handle_chan_modes(
        "IXZbegw,k,FHJLWdfjlx,ABCDKMNOPQRSTcimnprstuz", serv_info
    )
    users = chan_track.get_users(conn)
    chans = chan_track.get_chans(conn)

    chan = chans.getchan("#foo")
    assert chan.name == "#foo"

    chan.data["new_users"] = [
        "@+foo!bar@baz",
        "@ExampleUser!bar@baz",
        "-ExampleUser2!bar@baz",
        "!@%+-foo1!bar@baz",
    ]
    chan_track.replace_user_data(conn, chan)

    assert users["exampleuser"].host == "baz"

    test_user = users["exampleuser2"]
    chan_track.on_nick("exampleuser2", ["ExampleUserFoo"], conn)

    assert test_user.nick == "ExampleUserFoo"
    assert "exampleuserfoo" in chan.users

    user = users.getuser("exampleuserfoo")

    assert chan.get_member(user).status == conn.get_statuses("-")

    chan_track.on_join("nick1", "user", "host", conn, ["#bar"])

    assert users["Nick1"].host == "host"

    assert chans["#Bar"].users["Nick1"].status == conn.get_statuses("")

    chan_track.on_mode(chan.name, [chan.name, "+sop", test_user.nick], conn)

    assert chan.get_member(test_user).status == conn.get_statuses("@-")

    chan_track.on_part(chan.name, test_user.nick, conn)

    assert test_user.nick not in chan.users

    assert "foo" in chan.users
    chan_track.on_kick(chan.name, "foo", conn)
    assert "foo" not in chan.users

    assert "foo1" in chan.users
    chan_track.on_quit("foo1", conn)
    assert "foo1" not in chan.users


NAMES_MOCK_TRAFFIC = [
    ":BotFoo!myname@myhost JOIN #foo",
    ":server.name 353 BotFoo = #foo :BotFoo",
    ":server.name 353 BotFoo = #foo :OtherUser PersonC",
    ":QuickUser!user@host JOIN #foo",
    ":OtherQuickUser!user@host JOIN #foo",
    ":server.name 353 BotFoo = #foo :FooBar123",
    ":server.name 366 BotFoo #foo :End of /NAMES list",
    ":QuickUser!user@host PART #foo",
    ":BotFoo!myname@myhost KICK #foo OtherQuickUser",
]


def test_names_handling(event_loop):
    handlers = {
        "JOIN": chan_track.on_join,
        "PART": chan_track.on_part,
        "QUIT": chan_track.on_quit,
        "KICK": chan_track.on_kick,
        "353": chan_track.on_names,
        "366": chan_track.on_names,
    }

    bot = MagicMock()
    bot.loop = event_loop

    conn = MockConn(bot)
    serv_info = conn.memory["server_info"]
    server_info.handle_prefixes("(YohvV)!@%+-", serv_info)
    server_info.handle_chan_modes(
        "IXZbegw,k,FHJLWdfjlx,ABCDKMNOPQRSTcimnprstuz", serv_info
    )

    for line in NAMES_MOCK_TRAFFIC:
        event = _IrcProtocol(conn=conn).parse_line(line)
        call_with_args(handlers[event.irc_command], event)


def test_account_tag(event_loop):
    bot = MagicMock()
    bot.loop = event_loop

    conn = MockConn(bot)
    data = {
        "conn": conn,
        "irc_tags": TagList.from_dict({"account": "foo"}),
        "nick": "bar",
    }
    user = chan_track.get_users(conn).getuser("bar")
    assert user.account is None
    res = call_with_args(chan_track.handle_tags, data)
    assert res is None
    assert dict(chan_track.get_users(conn)) == {"bar": user}
    assert user.account == "foo"

    data = {
        "conn": conn,
        "irc_tags": TagList.from_dict({"account": "*"}),
        "nick": "bar",
    }
    res = call_with_args(chan_track.handle_tags, data)
    assert res is None
    assert dict(chan_track.get_users(conn)) == {"bar": user}
    assert user.account is None


class TestSerializer:
    def test_simple(self):
        assert chan_track.MappingSerializer().serialize("a") == '"a"'
        assert chan_track.MappingSerializer().serialize(1) == "1"
        assert chan_track.MappingSerializer().serialize(None) == "null"
        assert chan_track.MappingSerializer().serialize(True) == "true"

    def test_dict(self):
        assert (
            chan_track.MappingSerializer().serialize({"a": 1, "b": True})
            == '{"a": 1, "b": true}'
        )

    def test_int_list(self):
        assert (
            chan_track.MappingSerializer().serialize([1, 2, 3]) == "[1, 2, 3]"
        )
