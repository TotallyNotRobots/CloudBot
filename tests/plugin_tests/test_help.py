from unittest.mock import MagicMock

import pytest

from cloudbot import hook
from cloudbot.event import CommandEvent, Event
from cloudbot.plugin import PluginManager
from plugins.core import help as help_plugin
from tests.util import wrap_hook_response, wrap_hook_response_async
from tests.util.mock_module import MockModule


@pytest.mark.asyncio
async def test_help_command(
    patch_import_module, patch_import_reload, tmp_path
) -> None:
    conn = MagicMock(config={})
    conn.bot.plugin_manager = manager = PluginManager(conn.bot)
    conn.bot.base_dir = tmp_path
    conn.bot.config = {}

    @hook.command("foo")
    def cmd_foo() -> None:
        """- foo bar"""

    @hook.command("bar")
    def cmd_bar() -> None:
        """- bar foo"""

    plugin_code = MockModule("foobar", cmd_foo=cmd_foo, cmd_bar=cmd_bar)

    patch_import_module.return_value = plugin_code
    patch_import_reload.return_value = plugin_code
    await manager.load_plugin(tmp_path / "plugins" / "file.py")
    event = CommandEvent(
        hook=MagicMock(),
        text="",
        triggered_command="help",
        cmd_prefix=".",
        base_event=Event(
            channel="#foo", conn=conn, bot=conn.bot, nick="testnick"
        ),
    )

    assert wrap_hook_response(help_plugin.help_command, event) == [
        (
            "notice",
            ("testnick", "Here's a list of commands you can use: bar, foo"),
        ),
        (
            "notice",
            (
                "testnick",
                "For detailed help, use .help <command>, without the brackets.",
            ),
        ),
    ]

    assert conn.mock_calls == []


@pytest.mark.asyncio
async def test_help_command_single(
    patch_import_module, patch_import_reload, tmp_path
) -> None:
    conn = MagicMock(config={})
    conn.bot.plugin_manager = manager = PluginManager(conn.bot)
    conn.bot.base_dir = tmp_path
    conn.bot.config = {}

    @hook.command("foo")
    def cmd_foo() -> None:
        """- foo bar"""

    @hook.command("bar")
    def cmd_bar() -> None:
        """- bar foo"""

    plugin_code = MockModule("foobar", cmd_foo=cmd_foo, cmd_bar=cmd_bar)

    patch_import_module.return_value = plugin_code
    patch_import_reload.return_value = plugin_code
    await manager.load_plugin(tmp_path / "plugins" / "file.py")
    event = CommandEvent(
        hook=MagicMock(),
        text="foo",
        triggered_command="help",
        cmd_prefix=".",
        base_event=Event(
            channel="#foo", conn=conn, bot=conn.bot, nick="testnick"
        ),
    )

    assert wrap_hook_response(help_plugin.help_command, event) == [
        ("notice", ("testnick", ".foo - foo bar"))
    ]

    assert conn.mock_calls == []


@pytest.mark.asyncio
async def test_help_command_single_no_doc(
    patch_import_module, patch_import_reload, tmp_path
) -> None:
    conn = MagicMock(config={})
    conn.bot.plugin_manager = manager = PluginManager(conn.bot)
    conn.bot.base_dir = tmp_path
    conn.bot.config = {}

    @hook.command("foo")
    def cmd_foo() -> None:
        pass

    @hook.command("bar")
    def cmd_bar() -> None:
        """- bar foo"""

    plugin_code = MockModule("foobar", cmd_foo=cmd_foo, cmd_bar=cmd_bar)

    patch_import_module.return_value = plugin_code
    patch_import_reload.return_value = plugin_code
    await manager.load_plugin(tmp_path / "plugins" / "file.py")
    event = CommandEvent(
        hook=MagicMock(),
        text="foo",
        triggered_command="help",
        cmd_prefix=".",
        base_event=Event(
            channel="#foo", conn=conn, bot=conn.bot, nick="testnick"
        ),
    )

    assert wrap_hook_response(help_plugin.help_command, event) == [
        ("notice", ("testnick", "Command foo has no additional documentation."))
    ]

    assert conn.mock_calls == []


@pytest.mark.asyncio
async def test_cmdinfo(
    patch_import_module, patch_import_reload, tmp_path
) -> None:
    conn = MagicMock(config={})
    conn.bot.plugin_manager = manager = PluginManager(conn.bot)
    conn.bot.base_dir = tmp_path
    conn.bot.config = {}

    @hook.command("foo")
    def cmd_foo() -> None:
        """- foo bar"""

    @hook.command("bar")
    def cmd_bar() -> None:
        """- bar foo"""

    plugin_code = MockModule("foobar", cmd_foo=cmd_foo, cmd_bar=cmd_bar)

    patch_import_module.return_value = plugin_code
    patch_import_reload.return_value = plugin_code
    await manager.load_plugin(tmp_path / "plugins" / "file.py")
    event = CommandEvent(
        hook=MagicMock(),
        text="foo",
        triggered_command="cmdinfo",
        cmd_prefix=".",
        base_event=Event(
            channel="#foo", conn=conn, bot=conn.bot, nick="testnick"
        ),
    )

    assert await wrap_hook_response_async(help_plugin.cmdinfo, event) == [
        (
            "notice",
            (
                "testnick",
                "Command: foo, Aliases: [foo], Hook name: file.cmd_foo",
            ),
        )
    ]

    assert conn.mock_calls == []


@pytest.mark.asyncio
async def test_cmdinfo_perms(
    patch_import_module, patch_import_reload, tmp_path
) -> None:
    conn = MagicMock(config={})
    conn.bot.plugin_manager = manager = PluginManager(conn.bot)
    conn.bot.base_dir = tmp_path
    conn.bot.config = {}

    @hook.command("foo", permissions=["foo"])
    def cmd_foo() -> None:
        """- foo bar"""

    @hook.command("bar")
    def cmd_bar() -> None:
        """- bar foo"""

    plugin_code = MockModule("foobar", cmd_foo=cmd_foo, cmd_bar=cmd_bar)

    patch_import_module.return_value = plugin_code
    patch_import_reload.return_value = plugin_code
    await manager.load_plugin(tmp_path / "plugins" / "file.py")
    event = CommandEvent(
        hook=MagicMock(),
        text="foo",
        triggered_command="cmdinfo",
        cmd_prefix=".",
        base_event=Event(
            channel="#foo", conn=conn, bot=conn.bot, nick="testnick"
        ),
    )

    assert await wrap_hook_response_async(help_plugin.cmdinfo, event) == [
        (
            "notice",
            (
                "testnick",
                "Command: foo, Aliases: [foo], Hook name: file.cmd_foo, Permissions: [foo]",
            ),
        )
    ]

    assert conn.mock_calls == []
