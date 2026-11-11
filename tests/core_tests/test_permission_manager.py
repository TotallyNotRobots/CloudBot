from typing import TYPE_CHECKING, cast

import pytest

from cloudbot import permissions
from cloudbot.permissions import (
    Group,
    GroupMember,
    GroupPermission,
    PermissionManager,
)
from tests.util.mock_conn import MockClient

if TYPE_CHECKING:
    import sqlalchemy as sa


def model_to_dict(obj):
    cls = type(obj)
    out = {}
    for column in cls.__table__.c:
        out[column.name] = getattr(obj, column.name)

    return out


@pytest.mark.asyncio
async def test_manager_load(mock_db, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    group_table = Group.__table__
    group_member_table = GroupMember.__table__
    permission_table = GroupPermission.__table__
    manager = PermissionManager(MockClient(bot=bot, name="testconn", config={}))

    assert not manager.get_groups()
    assert not manager.get_group_permissions("foobar")
    assert not manager.get_group_users("foobar")
    assert not manager.get_user_permissions("foo!bar@baz")
    assert not manager.get_user_groups("foo!bar@baz")
    assert not manager.group_exists("baz")
    assert not manager.user_in_group("foo!bar@baz", "bing")

    permissions.backdoor = "*!user@host"

    assert manager.has_perm_mask("test!user@host", "foo", False)
    assert not manager.has_perm_mask("test!otheruser@host", "foo", False)

    user = "user!a@host.com"
    user_mask = "user!*@host??om"

    other_user = "user1!b@hosaacom"

    permissions.backdoor = None
    perm = "testperm"
    conn = MockClient(
        bot=bot,
        name="testconn",
        config={
            "permissions": {"admins": {"users": [user_mask], "perms": [perm]}}
        },
    )
    manager = PermissionManager(conn)
    assert manager.group_exists("admins")
    assert [model_to_dict(item) for item in manager.get_groups()] == [
        {"name": "admins", "connection": conn.name, "config": True}
    ]
    assert [model_to_dict(item) for item in manager.get_user_groups(user)] == [
        {"config": True, "connection": conn.name, "name": "admins"}
    ]
    assert not manager.get_user_groups(other_user)
    assert manager.get_group_users("admins") == [user_mask]
    assert manager.get_group_permissions("admins") == [perm]
    assert manager.get_user_permissions(user) == {perm}
    assert not manager.get_user_permissions(other_user)
    assert mock_db.get_data(group_table) == [(conn.name, "admins", True)]

    assert mock_db.get_data(group_member_table) == [
        (conn.name, "admins", "user!*@host??om", True)
    ]

    assert mock_db.get_data(permission_table) == [
        (conn.name, "admins", perm, True)
    ]
    assert manager.get_perm_users(perm) == ["user!*@host??om"]
    assert manager.user_in_group(user, "admins")
    assert not manager.user_in_group(other_user, "admins")
    assert manager.has_perm_mask(user, perm)

    assert manager.remove_group_user("admins", user) == [user_mask]

    assert "admins" not in manager.get_user_groups(user)
    assert user_mask not in manager.get_group_users("admins")
    assert perm not in manager.get_user_permissions(user)
    assert not manager.has_perm_mask(user, perm)
    assert not manager.user_in_group(user, "admins")


@pytest.mark.asyncio
async def test_add_user_to_group(mock_db, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    manager = PermissionManager(MockClient(bot=bot, name="testconn", config={}))
    manager.add_user_to_group("*!*@host", "admins")
    manager.add_user_to_group("*!*@mask", "admins")
    assert manager.user_in_group("user!name@host", "admins")
    assert manager.user_in_group("otheruser!name@mask", "admins")
    manager.add_user_to_group("*!*@mask", "admins")
    assert len(manager.get_group_users("admins")) == 2


@pytest.mark.asyncio
async def test_db(mock_db, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    session = mock_db.session()

    group_table = cast("sa.Table", Group.__table__)
    group_member_table = cast("sa.Table", GroupMember.__table__)
    permission_table = cast("sa.Table", GroupPermission.__table__)

    group_table.create(mock_db.engine)
    group_member_table.create(mock_db.engine)
    permission_table.create(mock_db.engine)

    conn = MockClient(bot=bot, name="testconn")

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

    res = (
        session.query(GroupMember.mask)
        .filter(
            GroupMember.group_id.in_(
                session.query(GroupPermission.group_id).filter(
                    GroupPermission.name == perm
                )
            )
        )
        .all()
    )

    assert res == [("thing",), ("thing1",)]

    conn = MockClient(
        bot=bot,
        config={
            "permissions": {
                "admins": {"users": ["a", "d"], "perms": ["foo"]},
                "foo": {"users": ["b", "c", "thing"], "perms": ["bar", "baz"]},
            }
        },
    )
    manager = PermissionManager(conn)

    assert mock_db.get_data(group_table) == [
        (conn.name, "foo", True),
        (conn.name, "foo1", False),
        (conn.name, "admins", True),
    ]

    assert mock_db.get_data(group_member_table) == [
        (conn.name, "foo", "thing", True),
        (conn.name, "foo1", "thing1", False),
        (conn.name, "admins", "a", True),
        (conn.name, "admins", "d", True),
        (conn.name, "foo", "b", True),
        (conn.name, "foo", "c", True),
    ]

    assert mock_db.get_data(permission_table) == [
        (conn.name, "foo", "bar", True),
        (conn.name, "foo1", "bar", False),
        (conn.name, "admins", "foo", True),
        (conn.name, "foo", "baz", True),
    ]

    assert manager.has_perm_mask("a", "foo", notice=False)
    assert not manager.has_perm_mask("b", "foo", notice=False)
    assert not manager.has_perm_mask("b", "foo", notice=True)


@pytest.mark.asyncio
async def test_db_config_merge(mock_db, mock_bot_factory) -> None:
    bot = mock_bot_factory(db=mock_db)
    session = mock_db.session()

    group_table = cast("sa.Table", Group.__table__)
    group_member_table = cast("sa.Table", GroupMember.__table__)
    permission_table = cast("sa.Table", GroupPermission.__table__)

    group_table.create(mock_db.engine)
    group_member_table.create(mock_db.engine)
    permission_table.create(mock_db.engine)

    conn = MockClient(bot=bot, name="testconn")

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

    conn = MockClient(
        bot=bot,
        name="testconn",
        config={
            "permissions": {
                "admins": {"users": ["a", "d"], "perms": ["foo"]},
                "foo": {"users": ["b", "c", "thing"], "perms": ["bar", "baz"]},
            }
        },
    )

    manager = PermissionManager(conn)

    assert mock_db.get_data(group_table) == [
        (conn.name, "foo", True),
        (conn.name, "foo1", False),
        (conn.name, "admins", True),
    ]

    assert mock_db.get_data(group_member_table) == [
        (conn.name, "foo", "thing", True),
        (conn.name, "foo1", "thing1", False),
        (conn.name, "admins", "a", True),
        (conn.name, "admins", "d", True),
        (conn.name, "foo", "b", True),
        (conn.name, "foo", "c", True),
    ]

    assert mock_db.get_data(permission_table) == [
        (conn.name, "foo", "bar", True),
        (conn.name, "foo1", "bar", False),
        (conn.name, "admins", "foo", True),
        (conn.name, "foo", "baz", True),
    ]

    perm_config = conn.config["permissions"]
    perm_config["foo"]["perms"].pop()
    perm_config["foo"]["perms"].append("test")
    perm_config["foo"]["users"].pop()
    perm_config.pop("admins")

    manager.reload()

    assert mock_db.get_data(group_table) == [
        (conn.name, "foo", True),
        (conn.name, "foo1", False),
    ]

    assert mock_db.get_data(group_member_table) == [
        (conn.name, "foo1", "thing1", False),
        (conn.name, "foo", "b", True),
        (conn.name, "foo", "c", True),
    ]

    assert mock_db.get_data(permission_table) == [
        (conn.name, "foo", "bar", True),
        (conn.name, "foo1", "bar", False),
        (conn.name, "foo", "test", True),
    ]

    assert manager.remove_group_user("other", "test") == []

    assert manager.remove_group_user("foo", "missing") == []
