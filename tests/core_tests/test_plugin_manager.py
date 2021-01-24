import itertools
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Column, String, Table

from cloudbot import hook
from cloudbot.event import EventType
from cloudbot.plugin import Plugin
from cloudbot.util import database
from tests.util.mock_bot import MockBot
from tests.util.mock_db import MockDB
from tests.util.mock_module import MockModule


@pytest.fixture()
def mock_bot():
    tmp_base = Path().resolve()
    tmp_base.mkdir(exist_ok=True)

    yield MockBot(base_dir=tmp_base)


@pytest.fixture()
def mock_manager(mock_bot):
    yield mock_bot.plugin_manager


def test_get_plugin(mock_manager):
    assert mock_manager.get_plugin("plugins/test.py") is None
    assert mock_manager.find_plugin("test") is None

    file_path = Path("plugins").resolve() / "test.py"
    file_name = file_path.name

    obj = Plugin(
        str(file_path),
        file_name,
        "test",
        MockModule(),
    )

    mock_manager._add_plugin(obj)

    assert mock_manager.get_plugin("plugins/test.py") is obj
    assert mock_manager.find_plugin("test") is obj

    mock_manager._rem_plugin(obj)

    assert mock_manager.get_plugin("plugins/test.py") is None
    assert mock_manager.find_plugin("test") is None


def test_can_load(mock_manager):
    mock_manager.bot.config.clear()

    assert mock_manager.can_load("plugins.foo")

    mock_manager.bot.config.update(
        {
            "plugin_loading": {
                "use_whitelist": True,
                "whitelist": [
                    "plugins.bar",
                ],
            }
        }
    )
    assert not mock_manager.can_load("plugins.foo")

    mock_manager.bot.config.update(
        {
            "plugin_loading": {
                "use_whitelist": True,
                "whitelist": [
                    "plugins.foo",
                ],
            }
        }
    )
    assert mock_manager.can_load("plugins.foo")

    mock_manager.bot.config.update(
        {
            "plugin_loading": {
                "use_whitelist": False,
                "whitelist": [
                    "plugins.bar",
                ],
                "blacklist": [
                    "plugins.foo",
                ],
            }
        }
    )
    assert not mock_manager.can_load("plugins.foo")

    mock_manager.bot.config.update(
        {
            "plugin_loading": {
                "use_whitelist": False,
                "whitelist": [
                    "plugins.bar",
                ],
                "blacklist": [],
            }
        }
    )
    assert mock_manager.can_load("plugins.foo")


@pytest.fixture()
def patch_import_module():
    with patch("importlib.import_module") as mocked:
        yield mocked


@pytest.fixture()
def patch_import_reload():
    with patch("importlib.reload") as mocked:
        yield mocked


def test_plugin_load(mock_manager, patch_import_module, patch_import_reload):
    patch_import_module.return_value = mod = MockModule()
    mock_manager.bot.loop.run_until_complete(
        mock_manager.load_plugin("plugins/test.py")
    )
    patch_import_module.assert_called_once_with("plugins.test")
    patch_import_reload.assert_not_called()
    assert mock_manager.get_plugin("plugins/test.py").code is mod

    patch_import_module.reset_mock()

    patch_import_reload.return_value = newmod = MockModule()

    mock_manager.bot.loop.run_until_complete(
        mock_manager.load_plugin("plugins/test.py")
    )

    patch_import_module.assert_called_once_with("plugins.test")
    patch_import_reload.assert_called_once_with(mod)

    assert mock_manager.get_plugin("plugins/test.py").code is newmod


class WeirdObject:
    """
    This represents an object that returns a value for any attribute you ask for
    """

    def __init__(self, func):
        self.func = func

    def __getattr__(self, item):
        return self.func(self, item)


def _test_weird_obj(patch_import_module, mock_manager, weird_obj):
    patch_import_module.return_value = MockModule(some_import=weird_obj)

    mock_manager.bot.loop.run_until_complete(
        mock_manager.load_plugin("plugins/test.py")
    )


def test_plugin_with_objs_none_attr(mock_manager, patch_import_module):
    _test_weird_obj(
        patch_import_module, mock_manager, WeirdObject(lambda *args: None)
    )


def test_plugin_with_objs_mock_attr(mock_manager, patch_import_module):
    _test_weird_obj(
        patch_import_module,
        mock_manager,
        WeirdObject(lambda *args: MagicMock()),
    )


def test_plugin_with_objs_dict_attr(mock_manager, patch_import_module):
    _test_weird_obj(
        patch_import_module, mock_manager, WeirdObject(lambda *args: {})
    )


def test_plugin_with_objs_full_dict_attr(mock_manager, patch_import_module):
    _test_weird_obj(
        patch_import_module,
        mock_manager,
        WeirdObject(
            lambda *args: {
                "some_thing": object(),
            }
        ),
    )


def test_plugin_load_disabled(
    mock_manager, patch_import_module, patch_import_reload
):
    patch_import_module.return_value = MockModule()
    mock_manager.bot.config.update(
        {
            "plugin_loading": {
                "use_whitelist": True,
                "whitelist": [
                    "plugins.bar",
                ],
            }
        }
    )
    assert (
        mock_manager.bot.loop.run_until_complete(
            mock_manager.load_plugin("plugins/test.py")
        )
        is None
    )

    patch_import_module.assert_not_called()
    patch_import_reload.assert_not_called()
    assert mock_manager.get_plugin("plugins/test.py") is None


class TestPluginLoad:
    @pytest.mark.asyncio
    async def test_duplicate_command(
        self,
        mock_manager,
        tmp_path,
        mock_bot,
        patch_import_module,
        patch_import_reload,
        caplog,
    ):
        plugin_a = MockModule()
        plugin_b = MockModule()

        @hook.command("foo")
        def cmd_func():
            raise NotImplementedError

        @hook.command("foo")
        def cmd_func_2():
            raise NotImplementedError

        plugin_a.cmd_func = cmd_func
        plugin_b.cmd_func_2 = cmd_func_2

        patch_import_module.return_value = plugin_a
        plugin_dir = mock_bot.base_dir / "plugins"
        plugin_dir.mkdir(exist_ok=True)
        (plugin_dir / "__init__.py").touch()
        plugin_file = plugin_dir / "test.py"
        plugin_file.touch()

        await mock_manager.load_plugin(str(plugin_file))

        assert caplog.record_tuples == [
            ("cloudbot", 20, "Loaded command foo from test.py"),
            (
                "cloudbot",
                10,
                "Loaded Command[name: foo, aliases: [], type: command, plugin: test, "
                "permissions: [], single_thread: False, threaded: True]",
            ),
        ]
        patch_import_module.return_value = plugin_b
        plugin_file_b = plugin_file.with_name("test2.py")
        plugin_file_b.touch()
        caplog.clear()
        await mock_manager.load_plugin(str(plugin_file_b))

        assert caplog.record_tuples == [
            (
                "cloudbot",
                30,
                "Plugin test2 attempted to register command foo which was already registered "
                "by test. Ignoring new assignment.",
            ),
            ("cloudbot", 20, "Loaded command foo from test2.py"),
            (
                "cloudbot",
                10,
                "Loaded Command[name: foo, aliases: [], type: command, plugin: test2, "
                "permissions: [], single_thread: False, threaded: True]",
            ),
        ]

        assert mock_manager.commands["foo"].function is cmd_func

        await mock_manager.unload_plugin(str(plugin_file))
        await mock_manager.unload_plugin(str(plugin_file_b))


@pytest.mark.asyncio
async def test_load_all(
    mock_manager, tmp_path, mock_bot, patch_import_module, patch_import_reload
):
    mod = MockModule()

    @hook.command("foo")
    def cmd_func():
        raise NotImplementedError

    started = 0
    stopped = 0

    @hook.on_start()
    def start():
        nonlocal started
        started += 1

    @hook.on_stop()
    def stop():
        nonlocal stopped
        stopped += 1

    mod.cmd_func = cmd_func
    mod.start = start
    mod.stop = stop

    patch_import_module.return_value = mod
    plugin_dir = mock_bot.base_dir / "plugins"
    plugin_dir.mkdir(exist_ok=True)
    (plugin_dir / "__init__.py").touch()
    plugin_file = plugin_dir / "test.py"
    plugin_file.touch()

    await mock_manager.load_all(str(plugin_dir))
    assert "foo" in mock_manager.commands
    assert mock_manager.commands["foo"].function is cmd_func
    assert started == 1
    assert stopped == 0

    await mock_manager.unload_all()

    assert stopped == 1

    assert "foo" not in mock_manager.commands


@pytest.mark.asyncio
async def test_load_on_start_error(
    mock_manager,
    tmp_path,
    mock_bot,
    patch_import_module,
    patch_import_reload,
    caplog,
):
    mod = MockModule()

    @hook.on_start()
    def start():
        raise ValueError

    mod.start = start

    patch_import_module.return_value = mod
    plugin_dir = mock_bot.base_dir / "plugins"
    plugin_dir.mkdir(exist_ok=True)
    (plugin_dir / "__init__.py").touch()
    plugin_file = plugin_dir / "test.py"
    plugin_file.touch()

    await mock_manager.load_plugin(str(plugin_file))

    assert caplog.record_tuples == [
        ("cloudbot", 40, "Error in hook test:start"),
        (
            "cloudbot",
            30,
            "Not registering hooks from plugin test: on_start hook errored",
        ),
    ]
    assert not mock_manager.plugins


@pytest.mark.asyncio
async def test_load_config_hooks(
    mock_manager,
    tmp_path,
    mock_bot,
    patch_import_module,
    patch_import_reload,
    caplog,
):
    mod = MockModule()

    @hook.config()
    def config():
        raise NotImplementedError

    mod.config = config
    patch_import_module.return_value = mod
    plugin_dir = mock_bot.base_dir / "plugins"
    plugin_dir.mkdir(exist_ok=True)
    (plugin_dir / "__init__.py").touch()
    plugin_file = plugin_dir / "test.py"
    plugin_file.touch()

    await mock_manager.load_plugin(str(plugin_file))

    assert caplog.record_tuples == [
        ("cloudbot", 20, "Loaded Config hook config from test.py"),
        (
            "cloudbot",
            10,
            "Loaded ConfigHook[type: config, plugin: test, permissions: [], "
            "single_thread: False, threaded: True]",
        ),
    ]
    assert len(mock_manager.config_hooks) == 1
    caplog.clear()

    await mock_manager.unload_plugin(str(plugin_file))
    assert len(mock_manager.config_hooks) == 0
    assert caplog.record_tuples == [
        ("cloudbot", 20, "Unloaded all plugins from test")
    ]


@pytest.mark.asyncio
async def test_unload_raw_hooks(
    mock_manager,
    tmp_path,
    mock_bot,
    patch_import_module,
    patch_import_reload,
    caplog,
):
    mod = MockModule()

    @hook.irc_raw("PRIVMSG")
    def irc_raw():
        raise NotImplementedError

    @hook.irc_raw("PRIVMSG")
    def irc_raw2():
        raise NotImplementedError

    mod.irc_raw = irc_raw
    mod.irc_raw2 = irc_raw2
    patch_import_module.return_value = mod
    plugin_dir = mock_bot.base_dir / "plugins"
    plugin_dir.mkdir(exist_ok=True)
    (plugin_dir / "__init__.py").touch()
    plugin_file = plugin_dir / "test.py"
    plugin_file.touch()

    await mock_manager.load_plugin(str(plugin_file))

    caplog.clear()
    assert mock_manager.raw_triggers["PRIVMSG"][0].function is irc_raw

    await mock_manager.unload_plugin(str(plugin_file))

    assert len(mock_manager.raw_triggers["PRIVMSG"]) == 0
    assert caplog.record_tuples == [
        ("cloudbot", 20, "Unloaded all plugins from test")
    ]


@pytest.mark.asyncio
async def test_unload_event_hooks(
    mock_manager,
    tmp_path,
    mock_bot,
    patch_import_module,
    patch_import_reload,
    caplog,
):
    mod = MockModule()

    @hook.event(EventType.notice)
    def event():
        raise NotImplementedError

    @hook.event(EventType.notice)
    def event2():
        raise NotImplementedError

    mod.event = event
    mod.event2 = event2
    patch_import_module.return_value = mod
    plugin_dir = mock_bot.base_dir / "plugins"
    plugin_dir.mkdir(exist_ok=True)
    (plugin_dir / "__init__.py").touch()
    plugin_file = plugin_dir / "test.py"
    plugin_file.touch()

    await mock_manager.load_plugin(str(plugin_file))

    caplog.clear()
    assert mock_manager.event_type_hooks[EventType.notice][0].function is event

    await mock_manager.unload_plugin(str(plugin_file))

    assert len(mock_manager.event_type_hooks[EventType.notice]) == 0
    assert caplog.record_tuples == [
        ("cloudbot", 20, "Unloaded all plugins from test")
    ]


def test_safe_resolve(mock_manager):
    base_path = Path("/some/path/that/doesn't/exist")
    path = mock_manager.safe_resolve(base_path)
    assert str(path) == str(base_path.absolute())
    assert path.is_absolute()
    assert not path.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "do_sieve,sieve_allow,single_thread,sieve_error",
    list(
        itertools.product(
            [True, False], [True, False], [True, False], [True, False]
        )
    ),
)
async def test_launch(
    mock_manager,
    patch_import_module,
    do_sieve,
    sieve_allow,
    single_thread,
    sieve_error,
    caplog,
):
    called = False
    sieve_called = False
    post_called = 0

    @hook.command("test", do_sieve=do_sieve, singlethread=single_thread)
    def foo_cb():
        nonlocal called
        called = True

    @hook.sieve()
    @hook.sieve()
    def sieve_cb(_bot, _event, _hook):
        nonlocal sieve_called
        sieve_called = True
        if sieve_error:
            raise Exception()

        if sieve_allow:
            return _event

        return None

    @hook.post_hook()
    def post_hook():
        nonlocal post_called
        post_called += 1

    mod = MockModule()

    mod.sieve_cb = sieve_cb
    mod.foo_cb = foo_cb
    mod.post_hook = post_hook

    patch_import_module.return_value = mod

    await mock_manager.load_plugin("plugins/test.py")

    from cloudbot.event import CommandEvent

    event = CommandEvent(
        bot=mock_manager.bot,
        hook=mock_manager.commands["test"],
        cmd_prefix=".",
        text="",
        triggered_command="test",
    )
    caplog.clear()
    result = await mock_manager.launch(event.hook, event)
    if do_sieve:
        if sieve_allow and not sieve_error:
            expected_post = 2
        else:
            expected_post = 1
    else:
        expected_post = 1

    if sieve_error and sieve_called:
        assert result == called and not called
        assert caplog.record_tuples == [
            (
                "cloudbot",
                40,
                "Error running sieve test:sieve_cb on test:foo_cb:",
            )
        ]
    else:
        assert result == called and called == (sieve_allow or not do_sieve)

    assert sieve_called == do_sieve
    assert post_called == expected_post


@pytest.mark.asyncio
async def test_create_tables(caplog, tmp_path):
    db = MockDB("sqlite:///" + str(tmp_path / "database.db"))
    bot = MockBot(db=db)
    assert database.metadata is not None
    database.metadata.bind = bot.db_engine
    table = Table(
        "test",
        database.metadata,
        Column("a", String),
    )
    plugin = MagicMock()
    plugin.title = "test.py"
    plugin.tables = [table]
    await Plugin.create_tables(plugin, bot)
    assert [t for t in caplog.record_tuples if t[0] == "cloudbot"] == [
        ("cloudbot", 20, "Registering tables for test.py"),
    ]
    assert plugin.mock_calls == []
    assert table.exists(bot.db_engine)
