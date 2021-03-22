from unittest.mock import MagicMock

from plugins import link_announcer, yelling


def test_yell_check():
    conn = MagicMock()
    bot = conn.bot
    plugin_manager = bot.plugin_manager

    plugin_manager.find_plugin.return_value = None
    yelling.yell_check(conn, "#yelling", "aaaaaaaaaaaaaa", bot, "testuser")

    conn.cmd.assert_called_with(
        "KICK", "#yelling", "testuser", "USE MOAR CAPS YOU TROGLODYTE!"
    )
    conn.cmd.reset_mock()

    yelling.yell_check(conn, "#yelling", "AAAAAAAAAAAAAAAAA", bot, "testuser")

    conn.cmd.assert_not_called()
    conn.cmd.reset_mock()

    yelling.yell_check(conn, "#yelling", "11", bot, "testuser")

    conn.cmd.assert_not_called()
    conn.cmd.reset_mock()

    yelling.yell_check(conn, "#yelling1", "11", bot, "testuser")

    conn.cmd.assert_not_called()
    conn.cmd.reset_mock()

    plugin_manager.find_plugin.return_value = fake_plugin = MagicMock()

    fake_plugin.code.url_re = link_announcer.url_re

    yelling.yell_check(
        conn, "#yelling", "http://a aaaaaaaaaaaaaaaaaaaaaa", bot, "testuser"
    )

    conn.cmd.assert_called_with(
        "KICK", "#yelling", "testuser", "USE MOAR CAPS YOU TROGLODYTE!"
    )
    conn.cmd.reset_mock()
