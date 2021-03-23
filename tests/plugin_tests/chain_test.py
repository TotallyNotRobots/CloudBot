from unittest.mock import MagicMock, call

from cloudbot.hook import command
from cloudbot.plugin import Plugin
from cloudbot.plugin_hooks import CommandHook
from cloudbot.util import HOOK_ATTR
from plugins import chain
from tests.util.mock_module import MockModule


def _get_hook(func, name):
    return getattr(func, HOOK_ATTR)[name]


def test_chainlist_empty(mock_db, mock_bot_factory):
    mock_bot = mock_bot_factory(db=mock_db)
    chain.commands.create(mock_db.engine)
    chain.load_cache(mock_db.session())
    event = MagicMock()
    res = chain.chainlist(mock_bot, event)
    assert res is None
    assert event.mock_calls == []


def test_chainlist(mock_db, mock_bot_factory):
    mock_bot = mock_bot_factory(db=mock_db)

    @command()
    def func():
        raise NotImplementedError

    mock_bot.plugin_manager.commands["bar"] = CommandHook(
        Plugin("test/foo.py", "foo.py", "foo", MockModule()),
        _get_hook(func, "command"),
    )
    db = mock_db.session()
    chain.commands.create(mock_db.engine)
    event = MagicMock()
    mock_db.add_row(chain.commands, hook="foo.func", allowed=True)
    chain.load_cache(db)
    res = chain.chainlist(mock_bot, event)
    assert res is None
    assert event.mock_calls == [call.notice("func")]
