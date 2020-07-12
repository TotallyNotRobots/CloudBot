from unittest.mock import MagicMock

from cloudbot.event import CommandEvent
from cloudbot.permissions import PermissionManager
from plugins import admin_bot
from tests.util import wrap_hook_response
from tests.util.mock_bot import MockConfig


def test_get_permission_groups():
    bot = MagicMock()
    conn = MagicMock(bot=bot)
    bot.connections = [conn]
    conn.name = "fooconn"
    conn.config = MockConfig(bot)
    conn.config.update(
        {
            "permissions": {
                "admin": {"perms": ["admin", "foo"], "users": ["foobar", "baz"]}
            }
        }
    )

    conn.permissions = PermissionManager(conn)
    assert admin_bot.get_permission_groups(conn) == "Valid groups: {'admin'}"


def test_get_group_permissions():
    bot = MagicMock()
    conn = MagicMock(bot=bot)
    bot.connections = [conn]
    conn.name = "fooconn"
    conn.config = MockConfig(bot)
    conn.config.update(
        {
            "permissions": {
                "admin": {"perms": ["admin", "foo"], "users": ["foobar", "baz"]}
            }
        }
    )

    conn.permissions = PermissionManager(conn)
    hook = MagicMock()
    event = CommandEvent(
        text="admin",
        triggered_command="gperms",
        cmd_prefix=".",
        hook=hook,
        conn=conn,
    )
    assert wrap_hook_response(admin_bot.get_group_permissions, event) == [
        ("return", "Group admin has permissions ['admin', 'foo']")
    ]

    event = CommandEvent(
        text="foobar",
        triggered_command="gperms",
        cmd_prefix=".",
        hook=hook,
        conn=conn,
        nick="foonick",
    )
    assert wrap_hook_response(admin_bot.get_group_permissions, event) == [
        ("notice", ("foonick", "Unknown group 'foobar'"))
    ]
