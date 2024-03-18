from unittest.mock import MagicMock, call

from cloudbot import hook
from cloudbot.hook import command
from cloudbot.plugin import Plugin
from cloudbot.plugin_hooks import CommandHook
from cloudbot.util import HOOK_ATTR
from plugins import chain
from tests.util.mock_bot import MockBot
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


def test_chainallow_bad_subcmd(mock_db, mock_bot_factory):
    mock_bot = mock_bot_factory(db=mock_db)
    db = mock_db.session()
    notice_doc = MagicMock(return_value=None)
    res = chain.chainallow("foo bar", db, notice_doc, mock_bot)
    assert res is None
    assert notice_doc.mock_calls == [call()]


def test_chainallow_add_no_args(mock_db, mock_bot_factory):
    mock_bot = mock_bot_factory(db=mock_db)
    db = mock_db.session()
    notice_doc = MagicMock(return_value=None)
    res = chain.chainallow("add", db, notice_doc, mock_bot)
    assert res is None
    assert notice_doc.mock_calls == [call()]


def test_chainallow_add_no_cmd(mock_db, mock_bot_factory):
    mock_bot = mock_bot_factory(db=mock_db)
    db = mock_db.session()
    notice_doc = MagicMock(return_value=None)
    res = chain.chainallow("add some.hook allow", db, notice_doc, mock_bot)
    assert res == "Unable to find command 'some.hook'"
    assert notice_doc.mock_calls == []


def test_chainallow_del_no_cmd(mock_db, mock_bot_factory):
    mock_bot = mock_bot_factory(db=mock_db)
    db = mock_db.session()
    notice_doc = MagicMock(return_value=None)
    res = chain.chainallow("del some.hook", db, notice_doc, mock_bot)
    assert res == "Unable to find command 'some.hook'"
    assert notice_doc.mock_calls == []


def test_chainallow_del_hook_not_set(mock_db, mock_bot_factory):
    @hook.command("foo")
    def hook_func():
        raise NotImplementedError

    @hook.command("bar")
    def other_hook_func():
        raise NotImplementedError

    mock_bot: MockBot = mock_bot_factory(db=mock_db)
    plugin = Plugin("plugins/foo.py", "foo.py", "foo", MockModule())
    mock_bot.plugin_manager.commands["foo"] = CommandHook(
        plugin,
        _get_hook(hook_func, "command"),
    )

    mock_bot.plugin_manager.commands["bar"] = CommandHook(
        plugin,
        _get_hook(other_hook_func, "command"),
    )

    chain.commands.create(mock_db.engine)
    db = mock_db.session()
    notice_doc = MagicMock(return_value=None)
    res = chain.chainallow("del foo.other_hook_func", db, notice_doc, mock_bot)
    assert res == "Deleted 0 rows."
    assert notice_doc.mock_calls == []

    assert mock_db.get_data(chain.commands) == []


def test_chainallow_del_hook(mock_db, mock_bot_factory):
    @hook.command("foo")
    def hook_func():
        raise NotImplementedError

    @hook.command("bar")
    def other_hook_func():
        raise NotImplementedError

    mock_bot: MockBot = mock_bot_factory(db=mock_db)
    plugin = Plugin("plugins/foo.py", "foo.py", "foo", MockModule())
    mock_bot.plugin_manager.commands["foo"] = CommandHook(
        plugin,
        _get_hook(hook_func, "command"),
    )

    mock_bot.plugin_manager.commands["bar"] = CommandHook(
        plugin,
        _get_hook(other_hook_func, "command"),
    )

    chain.commands.create(mock_db.engine)
    mock_db.load_data(
        chain.commands, [{"hook": "foo.other_hook_func", "allowed": False}]
    )

    db = mock_db.session()
    chain.load_cache(db)
    notice_doc = MagicMock(return_value=None)
    res = chain.chainallow("del foo.other_hook_func", db, notice_doc, mock_bot)
    assert res == "Deleted 1 row."
    assert notice_doc.mock_calls == []
    assert mock_db.get_data(chain.commands) == []


def test_chainallow_add_hook_no_arg(mock_db, mock_bot_factory):
    @hook.command("foo")
    def hook_func():
        raise NotImplementedError

    @hook.command("bar")
    def other_hook_func():
        raise NotImplementedError

    mock_bot: MockBot = mock_bot_factory(db=mock_db)
    plugin = Plugin("plugins/foo.py", "foo.py", "foo", MockModule())
    mock_bot.plugin_manager.commands["foo"] = CommandHook(
        plugin,
        _get_hook(hook_func, "command"),
    )

    mock_bot.plugin_manager.commands["bar"] = CommandHook(
        plugin,
        _get_hook(other_hook_func, "command"),
    )

    chain.commands.create(mock_db.engine)
    db = mock_db.session()
    notice_doc = MagicMock(return_value=None)
    res = chain.chainallow("add foo.other_hook_func", db, notice_doc, mock_bot)
    assert res == "Added 'foo.other_hook_func' as an allowed command"
    assert notice_doc.mock_calls == []

    assert mock_db.get_data(chain.commands) == [
        ("foo.other_hook_func", True),
    ]


def test_chainallow_add_hook_allow(mock_db, mock_bot_factory):
    @hook.command("foo")
    def hook_func():
        raise NotImplementedError

    @hook.command("bar")
    def other_hook_func():
        raise NotImplementedError

    mock_bot: MockBot = mock_bot_factory(db=mock_db)
    plugin = Plugin("plugins/foo.py", "foo.py", "foo", MockModule())
    mock_bot.plugin_manager.commands["foo"] = CommandHook(
        plugin,
        _get_hook(hook_func, "command"),
    )

    mock_bot.plugin_manager.commands["bar"] = CommandHook(
        plugin,
        _get_hook(other_hook_func, "command"),
    )

    chain.commands.create(mock_db.engine)
    db = mock_db.session()
    notice_doc = MagicMock(return_value=None)
    res = chain.chainallow(
        "add foo.other_hook_func allow", db, notice_doc, mock_bot
    )
    assert res == "Added 'foo.other_hook_func' as an allowed command"
    assert notice_doc.mock_calls == []

    assert mock_db.get_data(chain.commands) == [
        ("foo.other_hook_func", True),
    ]


def test_chainallow_add_hook_allow_update(mock_db, mock_bot_factory):
    @hook.command("foo")
    def hook_func():
        raise NotImplementedError

    @hook.command("bar")
    def other_hook_func():
        raise NotImplementedError

    mock_bot: MockBot = mock_bot_factory(db=mock_db)
    plugin = Plugin("plugins/foo.py", "foo.py", "foo", MockModule())
    mock_bot.plugin_manager.commands["foo"] = CommandHook(
        plugin,
        _get_hook(hook_func, "command"),
    )

    mock_bot.plugin_manager.commands["bar"] = CommandHook(
        plugin,
        _get_hook(other_hook_func, "command"),
    )

    chain.commands.create(mock_db.engine)
    mock_db.load_data(
        chain.commands, [{"hook": "foo.other_hook_func", "allowed": False}]
    )
    db = mock_db.session()
    chain.load_cache(db)

    notice_doc = MagicMock(return_value=None)
    res = chain.chainallow(
        "add foo.other_hook_func allow", db, notice_doc, mock_bot
    )
    assert (
        res
        == "Updated state of 'foo.other_hook_func' in chainallow to allowed=True"
    )
    assert notice_doc.mock_calls == []

    assert mock_db.get_data(chain.commands) == [
        ("foo.other_hook_func", True),
    ]


def test_chainallow_add_hook_deny(mock_db, mock_bot_factory):
    @hook.command("foo")
    def hook_func():
        raise NotImplementedError

    @hook.command("bar")
    def other_hook_func():
        raise NotImplementedError

    mock_bot: MockBot = mock_bot_factory(db=mock_db)
    plugin = Plugin("plugins/foo.py", "foo.py", "foo", MockModule())
    mock_bot.plugin_manager.commands["foo"] = CommandHook(
        plugin,
        _get_hook(hook_func, "command"),
    )

    mock_bot.plugin_manager.commands["bar"] = CommandHook(
        plugin,
        _get_hook(other_hook_func, "command"),
    )

    chain.commands.create(mock_db.engine)
    db = mock_db.session()
    notice_doc = MagicMock(return_value=None)
    res = chain.chainallow(
        "add foo.other_hook_func deny", db, notice_doc, mock_bot
    )
    assert res == "Added 'foo.other_hook_func' as a denied command"
    assert notice_doc.mock_calls == []

    assert mock_db.get_data(chain.commands) == [
        ("foo.other_hook_func", False),
    ]


def test_chainallow_add_hook_bad_arg(mock_db, mock_bot_factory):
    @hook.command("foo")
    def hook_func():
        raise NotImplementedError

    @hook.command("bar")
    def other_hook_func():
        raise NotImplementedError

    mock_bot: MockBot = mock_bot_factory(db=mock_db)
    plugin = Plugin("plugins/foo.py", "foo.py", "foo", MockModule())
    mock_bot.plugin_manager.commands["foo"] = CommandHook(
        plugin,
        _get_hook(hook_func, "command"),
    )

    mock_bot.plugin_manager.commands["bar"] = CommandHook(
        plugin,
        _get_hook(other_hook_func, "command"),
    )

    chain.commands.create(mock_db.engine)
    db = mock_db.session()
    notice_doc = MagicMock(return_value=None)
    res = chain.chainallow(
        "add foo.other_hook_func foo", db, notice_doc, mock_bot
    )
    assert res is None
    assert notice_doc.mock_calls == [call()]

    assert mock_db.get_data(chain.commands) == []


def test_chainallow_add_cmd(mock_db, mock_bot_factory):
    @hook.command("foo")
    def hook_func():
        raise NotImplementedError

    @hook.command("bar")
    def other_hook_func():
        raise NotImplementedError

    mock_bot: MockBot = mock_bot_factory(db=mock_db)
    plugin = Plugin("plugins/foo.py", "foo.py", "foo", MockModule())
    mock_bot.plugin_manager.commands["foo"] = CommandHook(
        plugin,
        _get_hook(hook_func, "command"),
    )

    mock_bot.plugin_manager.commands["bar"] = CommandHook(
        plugin,
        _get_hook(other_hook_func, "command"),
    )

    chain.commands.create(mock_db.engine)
    db = mock_db.session()
    notice_doc = MagicMock(return_value=None)
    res = chain.chainallow("add foo allow", db, notice_doc, mock_bot)
    assert res == "Added 'foo.hook_func' as an allowed command"
    assert notice_doc.mock_calls == []

    assert mock_db.get_data(chain.commands) == [
        ("foo.hook_func", True),
    ]


def test_chainallow_add_partial_cmd(mock_db, mock_bot_factory):
    @hook.command("foo")
    def hook_func():
        raise NotImplementedError

    @hook.command("bar")
    def other_hook_func():
        raise NotImplementedError

    mock_bot: MockBot = mock_bot_factory(db=mock_db)
    plugin = Plugin("plugins/foo.py", "foo.py", "foo", MockModule())
    mock_bot.plugin_manager.commands["foo"] = CommandHook(
        plugin,
        _get_hook(hook_func, "command"),
    )

    mock_bot.plugin_manager.commands["bar"] = CommandHook(
        plugin,
        _get_hook(other_hook_func, "command"),
    )

    chain.commands.create(mock_db.engine)
    db = mock_db.session()
    notice_doc = MagicMock(return_value=None)
    res = chain.chainallow("add fo allow", db, notice_doc, mock_bot)
    assert res == "Added 'foo.hook_func' as an allowed command"
    assert notice_doc.mock_calls == []

    assert mock_db.get_data(chain.commands) == [
        ("foo.hook_func", True),
    ]
