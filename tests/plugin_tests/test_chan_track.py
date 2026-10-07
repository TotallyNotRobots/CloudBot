from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from irclib.parser import Prefix, TagList

from cloudbot.clients.irc import _IrcProtocol
from cloudbot.util.func_utils import call_with_args
from plugins.core import chan_track, server_info
from plugins.core.cap import CapInfoExt
from tests.util.mock_conn import MockClient
from tests.util.mock_irc_client import MockIrcClient

if TYPE_CHECKING:
    from cloudbot.client import Client
    from cloudbot.util.irc import StatusMode


def get_statuses(conn: Client, chars: str) -> list[StatusMode]:
    return [server_info.get_server_info(conn).statuses[c] for c in chars]


@pytest.mark.asyncio
async def test_replace_user_data(mock_db, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    conn = MockClient(bot=bot)
    CapInfoExt.ensure(conn).server_caps.update(
        {
            "userhost-in-names": True,
            "multi-prefix": True,
        }
    )
    serv_info = server_info.get_server_info(conn)
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

    assert chan.users["foo"].status == get_statuses(conn, "@+")
    assert chan.users["exampleuser"].status == get_statuses(conn, "@")
    assert chan.users["Foo1"].status == get_statuses(conn, "!@%+-")
    assert not chan.users["exampleuser2"].status


@pytest.mark.asyncio
async def test_missing_on_nick(mock_db, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    conn = MockClient(bot=bot)
    chans = chan_track.get_chans(conn)
    chan = chans.getchan("#foo")

    with pytest.raises(chan_track.MemberNotFoundException):
        chan.users.pop("exampleuser3")


@pytest.mark.asyncio
async def test_channel_members(mock_db, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    conn = MockClient(bot=bot)
    CapInfoExt.ensure(conn).server_caps.update(
        {
            "userhost-in-names": True,
            "multi-prefix": True,
        }
    )

    serv_info = server_info.get_server_info(conn)
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

    assert chan.get_member(user).status == get_statuses(conn, "-")

    chan_track.on_join("nick1", "user", "host", conn, ["#bar"])

    assert users["Nick1"].host == "host"

    assert chans["#Bar"].users["Nick1"].status == get_statuses(conn, "")

    chan_track.on_mode(chan.name, [chan.name, "+sop", test_user.nick], conn)

    assert chan.get_member(test_user).status == get_statuses(conn, "@-")

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


@pytest.mark.asyncio
async def test_names_handling(mock_db, mock_bot_factory) -> None:
    handlers = {
        "JOIN": chan_track.on_join,
        "PART": chan_track.on_part,
        "QUIT": chan_track.on_quit,
        "KICK": chan_track.on_kick,
        "353": chan_track.on_names,
        "366": chan_track.on_names,
    }

    bot = mock_bot_factory(db=mock_db)

    conn = MockIrcClient(
        bot=bot,
        name="testconn",
        nick="BotFoo",
        config={
            "connection": {
                "server": "foo.invalid",
            },
        },
    )

    CapInfoExt.ensure(conn).server_caps.update(
        {
            "userhost-in-names": True,
            "multi-prefix": True,
        }
    )

    serv_info = server_info.get_server_info(conn)
    server_info.handle_prefixes("(YohvV)!@%+-", serv_info)
    server_info.handle_chan_modes(
        "IXZbegw,k,FHJLWdfjlx,ABCDKMNOPQRSTcimnprstuz", serv_info
    )

    for line in NAMES_MOCK_TRAFFIC:
        event = _IrcProtocol(conn=conn).parse_line(line)
        call_with_args(handlers[event.irc_command], event)


@pytest.mark.asyncio
async def test_account_tag(mock_db, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    conn = MockClient(bot=bot)
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
    def test_simple(self) -> None:
        assert chan_track.MappingSerializer().serialize("a") == '"a"'
        assert chan_track.MappingSerializer().serialize(1) == "1"
        assert chan_track.MappingSerializer().serialize(None) == "null"
        assert chan_track.MappingSerializer().serialize(True) == "true"

    def test_dict(self) -> None:
        assert (
            chan_track.MappingSerializer().serialize({"a": 1, "b": True})
            == '{"a": 1, "b": true}'
        )

    def test_int_list(self) -> None:
        assert (
            chan_track.MappingSerializer().serialize([1, 2, 3]) == "[1, 2, 3]"
        )
