from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast
from unittest.mock import MagicMock, call

import pytest

from cloudbot.event import CommandEvent
from cloudbot.permissions import (
    Group,
    GroupMember,
    GroupPermission,
    PermissionManager,
)
from cloudbot.util import func_utils
from plugins import admin_bot
from tests.util import wrap_hook_response
from tests.util.mock_conn import MockClient

if TYPE_CHECKING:
    import sqlalchemy as sa
    import sqlalchemy.orm as sa_orm

    from tests.util.mock_db import MockDB


@pytest.mark.parametrize(
    "chan,text,result",
    [("#foo", "bar", ("#foo", "bar")), ("#foo", "#bar baz", ("#bar", "baz"))],
)
def test_get_chan(chan, text, result) -> None:
    assert admin_bot.get_chan(chan, text) == result


@pytest.mark.parametrize(
    "text,chan,out",
    [
        ("foo", "#bar", ["foo"]),
        ("", "#bar", ["#bar"]),
        ("foo baz", "#bar", ["foo", "baz"]),
    ],
)
def test_parse_targets(text, chan, out) -> None:
    assert admin_bot.parse_targets(text, chan) == out


@pytest.mark.asyncio
async def test_reload_config() -> None:
    bot = MagicMock()
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    bot.reload_config.return_value = future
    future.set_result(True)
    res = await admin_bot.rehash_config(bot)
    assert res == "Config reloaded."
    assert bot.mock_calls == [call.reload_config()]


@pytest.mark.parametrize(
    "input_text,chan,key",
    [
        ("#channel key", "#channel", "key"),
        ("channel key", "#channel", "key"),
        ("#channel", "#channel", None),
        ("channel", "#channel", None),
    ],
)
def test_join(input_text, chan, key) -> None:
    conn = MagicMock()
    conn.config = {}
    conn.bot = None

    event = CommandEvent(
        text=input_text,
        cmd_prefix=".",
        triggered_command="join",
        hook=MagicMock(),
        bot=conn.bot,
        conn=conn,
        channel="#foo",
        nick="foobaruser",
    )

    func_utils.call_with_args(admin_bot.join, event)

    event.conn.join.assert_called_with(chan, key)


def test_me() -> None:
    event = MagicMock()
    event.chan = "#foo"
    event.nick = "bar"
    event.text = "do thing"

    def f(self, attr):
        return getattr(self, attr)

    event.__getitem__ = f
    event.event = event

    func_utils.call_with_args(admin_bot.me, event)
    assert event.mock_calls == [
        call.admin_log('bar used ME to make me ACT "do thing" in #foo.'),
        call.conn.ctcp("#foo", "ACTION", "do thing"),
    ]


@pytest.mark.asyncio
async def test_remove_permission_user(mock_db, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    conn = MockClient(bot=bot, nick="testconn")

    session = mock_db.session()

    group_table = cast("sa.Table", Group.__table__)
    group_member_table = cast("sa.Table", GroupMember.__table__)
    permission_table = cast("sa.Table", GroupPermission.__table__)

    manager = PermissionManager(conn)
    conn.permissions = manager
    perm = "bar"
    group = Group(
        name="foo",
        connection=conn.name,
        perms=[GroupPermission(name=perm)],
        members=[GroupMember(mask="thing")],
    )

    group1 = Group(
        name="foo1",
        connection=conn.name,
        perms=[GroupPermission(name=perm)],
        members=[GroupMember(mask="thing1")],
    )

    session.add(group)
    session.add(group1)

    session.commit()
    event = MagicMock()
    event.conn = conn
    event.nick = "foo"

    assert mock_db.get_data(group_table) == [
        (conn.name, "foo", False),
        (conn.name, "foo1", False),
    ]

    assert mock_db.get_data(group_member_table) == [
        (conn.name, "foo", "thing", False),
        (conn.name, "foo1", "thing1", False),
    ]

    assert mock_db.get_data(permission_table) == [
        (conn.name, "foo", "bar", False),
        (conn.name, "foo1", "bar", False),
    ]

    admin_bot.remove_permission_user("thing1", event, conn)

    assert event.mock_calls == [
        call.reply("Removed thing1 from foo1"),
        call.admin_log("foo used deluser remove thing1 from foo1."),
    ]

    assert mock_db.get_data(group_table) == [
        (conn.name, "foo", False),
        (conn.name, "foo1", False),
    ]

    assert mock_db.get_data(group_member_table) == [
        (conn.name, "foo", "thing", False)
    ]

    assert mock_db.get_data(permission_table) == [
        (conn.name, "foo", "bar", False),
        (conn.name, "foo1", "bar", False),
    ]


@pytest.mark.asyncio
async def test_remove_permission_user_too_many_args(
    mock_db, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    conn = MockClient(bot=bot, nick="testconn")

    session = mock_db.session()

    group_table = cast("sa.Table", Group.__table__)
    group_member_table = cast("sa.Table", GroupMember.__table__)
    permission_table = cast("sa.Table", GroupPermission.__table__)

    manager = PermissionManager(conn)
    conn.permissions = manager
    perm = "bar"
    group = Group(
        name="foo",
        connection=conn.name,
        perms=[GroupPermission(name=perm)],
        members=[GroupMember(mask="thing")],
    )

    group1 = Group(
        name="foo1",
        connection=conn.name,
        perms=[GroupPermission(name=perm)],
        members=[GroupMember(mask="thing1")],
    )

    session.add(group)
    session.add(group1)

    session.commit()
    event = MagicMock()
    event.conn = conn
    event.nick = "foo"

    assert mock_db.get_data(group_table) == [
        (conn.name, "foo", False),
        (conn.name, "foo1", False),
    ]

    assert mock_db.get_data(group_member_table) == [
        (conn.name, "foo", "thing", False),
        (conn.name, "foo1", "thing1", False),
    ]

    assert mock_db.get_data(permission_table) == [
        (conn.name, "foo", "bar", False),
        (conn.name, "foo1", "bar", False),
    ]

    admin_bot.remove_permission_user("thing1 a b c", event, conn)

    assert event.mock_calls == [call.notice("Too many arguments")]

    assert mock_db.get_data(group_table) == [
        (conn.name, "foo", False),
        (conn.name, "foo1", False),
    ]

    assert mock_db.get_data(group_member_table) == [
        (conn.name, "foo", "thing", False),
        (conn.name, "foo1", "thing1", False),
    ]

    assert mock_db.get_data(permission_table) == [
        (conn.name, "foo", "bar", False),
        (conn.name, "foo1", "bar", False),
    ]


@pytest.mark.asyncio
async def test_remove_permission_user_too_few_args(
    mock_db, mock_bot_factory
) -> None:
    bot = mock_bot_factory(db=mock_db)
    conn = MockClient(bot=bot, nick="testconn")

    session = mock_db.session()

    group_table = cast("sa.Table", Group.__table__)
    group_member_table = cast("sa.Table", GroupMember.__table__)
    permission_table = cast("sa.Table", GroupPermission.__table__)

    manager = PermissionManager(conn)
    conn.permissions = manager
    perm = "bar"
    group = Group(
        name="foo",
        connection=conn.name,
        perms=[GroupPermission(name=perm)],
        members=[GroupMember(mask="thing")],
    )

    group1 = Group(
        name="foo1",
        connection=conn.name,
        perms=[GroupPermission(name=perm)],
        members=[GroupMember(mask="thing1")],
    )

    session.add(group)
    session.add(group1)

    session.commit()
    event = MagicMock()
    event.conn = conn
    event.nick = "foo"

    assert mock_db.get_data(group_table) == [
        (conn.name, "foo", False),
        (conn.name, "foo1", False),
    ]

    assert mock_db.get_data(group_member_table) == [
        (conn.name, "foo", "thing", False),
        (conn.name, "foo1", "thing1", False),
    ]

    assert mock_db.get_data(permission_table) == [
        (conn.name, "foo", "bar", False),
        (conn.name, "foo1", "bar", False),
    ]

    admin_bot.remove_permission_user("", event, conn)

    assert event.mock_calls == [call.notice("Not enough arguments")]

    assert mock_db.get_data(group_table) == [
        (conn.name, "foo", False),
        (conn.name, "foo1", False),
    ]

    assert mock_db.get_data(group_member_table) == [
        (conn.name, "foo", "thing", False),
        (conn.name, "foo1", "thing1", False),
    ]

    assert mock_db.get_data(permission_table) == [
        (conn.name, "foo", "bar", False),
        (conn.name, "foo1", "bar", False),
    ]


def test_get_permission_groups(mock_db: MockDB) -> None:
    conn = MagicMock(nick="testconn", config={})
    conn.name = "testconn"

    session: sa_orm.Session = mock_db.session()

    group_table = cast("sa.Table", Group.__table__)
    group_member_table = cast("sa.Table", GroupMember.__table__)
    permission_table = cast("sa.Table", GroupPermission.__table__)

    group_table.create(mock_db.engine)
    group_member_table.create(mock_db.engine)
    permission_table.create(mock_db.engine)
    session.add_all(
        [
            Group(connection=conn.name, name="foo"),
            Group(connection=conn.name, name="bar"),
            Group(connection=conn.name, name="baz"),
        ]
    )
    session.commit()

    manager = PermissionManager(conn)
    conn.permissions = manager
    cmd_event = CommandEvent(
        text="",
        cmd_prefix=".",
        triggered_command="groups",
        hook=MagicMock(),
        conn=conn,
        bot=conn.bot,
        channel="#foo",
        nick="foobar",
    )
    assert wrap_hook_response(admin_bot.get_permission_groups, cmd_event) == [
        ("return", "Valid groups: ['bar', 'baz', 'foo']")
    ]
    assert conn.mock_calls == []
