import importlib
from unittest.mock import MagicMock

from cloudbot.event import CommandEvent
from plugins.core import help
from tests.util import wrap_hook_response


def test_get_potential_commands():
    bot = MagicMock()
    cmd = MagicMock()
    cmd1 = MagicMock()
    bot.plugin_manager.commands = {
        "foo": cmd,
        "foobar": cmd1,
    }
    assert list(help.get_potential_commands(bot, "foo")) == [("foo", cmd)]
    assert sorted(help.get_potential_commands(bot, "f")) == [
        ("foo", cmd),
        ("foobar", cmd1),
    ]
    assert list(help.get_potential_commands(bot, "g")) == []


def test_help_cmd():
    importlib.reload(help)
    event = CommandEvent(
        channel="#foo",
        text="",
        triggered_command="help",
        cmd_prefix=".",
        hook=MagicMock(),
        nick="foonick",
        conn=MagicMock(),
        bot=MagicMock(),
    )
    assert wrap_hook_response(help.help_command, event) == [
        ("message", ("foonick", "Here's a list of commands you can use: ")),
        (
            "message",
            (
                "foonick",
                "For detailed help, use .help <command>, without the brackets.",
            ),
        ),
    ]
