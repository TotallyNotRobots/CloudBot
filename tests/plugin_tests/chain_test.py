from unittest.mock import MagicMock

from cloudbot.event import CommandEvent
from plugins import chain
from tests.util import wrap_hook_response


def test_hook_name():
    hook = MagicMock()
    hook.plugin.title = "foo"
    hook.function.__name__ = "bar"
    assert chain.format_hook_name(hook) == "foo.bar"


def test_chainallow(mock_db):
    mock_db.create_table(chain.commands)
    hook = MagicMock()
    conn = MagicMock()
    bot = MagicMock(db_session=mock_db.session)
    foo_hook = MagicMock()
    foo_hook.plugin.title = "foo"
    foo_hook.function.__name__ = "bar"
    bot.plugin_manager.commands = {"foo": foo_hook}
    event = CommandEvent(
        text="add foo",
        triggered_command="chainallow",
        cmd_prefix=".",
        hook=hook,
        conn=conn,
        bot=bot,
    )
    hook.required_args = ["db"]
    event.prepare_threaded()
    res = wrap_hook_response(chain.chainallow, event)
    assert res == [("return", "Added 'foo.bar' as an allowed command")]
