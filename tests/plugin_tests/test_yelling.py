from unittest.mock import MagicMock


def test_yell_check():
    conn = MagicMock()
    bot = conn.bot
    plugin_manager = bot.plugin_manager

    from plugins.yelling import yell_check

    plugin_manager.find_plugin.return_value = None
    yell_check(conn, '#yelling', 'aaaaaaaaaaaaaa', bot, 'testuser')

    conn.cmd.assert_called_with('KICK', '#yelling', 'testuser', "USE MOAR CAPS YOU TROGLODYTE!")
    conn.cmd.reset_mock()

    yell_check(conn, '#yelling', '11', bot, 'testuser')

    conn.cmd.assert_not_called()
    conn.cmd.reset_mock()

    yell_check(conn, '#yelling1', '11', bot, 'testuser')

    conn.cmd.assert_not_called()
    conn.cmd.reset_mock()

    plugin_manager.find_plugin.return_value = fake_plugin = MagicMock()

    from plugins.link_announcer import url_re
    fake_plugin.code.url_re = url_re

    yell_check(conn, '#yelling', 'http://a aaaaaaaaaaaaaaaaaaaaaa', bot, 'testuser')

    conn.cmd.assert_called_with('KICK', '#yelling', 'testuser', "USE MOAR CAPS YOU TROGLODYTE!")
    conn.cmd.reset_mock()
