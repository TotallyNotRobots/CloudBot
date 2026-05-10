from __future__ import annotations

import asyncio
from itertools import product
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, call, patch

import pytest
from sqlalchemy import Column, String, Table

import cloudbot.bot
from cloudbot import hook
from cloudbot.bot import CloudBot, clean_name, get_cmd_regex
from cloudbot.event import Event, EventType
from cloudbot.hook import Action, Priority
from cloudbot.plugin_hooks import CommandHook, ConfigHook, EventHook, RawHook
from cloudbot.util import database
from tests.util.async_mock import AsyncMock
from tests.util.mock_conn import MockClient
from tests.util.mock_db import MockDB

if TYPE_CHECKING:
    from collections.abc import Callable

    from tests.util.mock_bot import MockBot


@pytest.mark.asyncio
async def test_get_connection_configs(
    mock_bot_factory: Callable[..., MockBot],
) -> None:
    mock_bot = mock_bot_factory(config={"connections": [{"name": "foo"}]})
    assert mock_bot.get_connection_configs() == {
        "foo": {
            "name": "foo",
        },
    }


@pytest.mark.asyncio
async def test_get_connection_configs_with_dupes(
    mock_bot_factory: Callable[..., MockBot],
) -> None:
    mock_bot = mock_bot_factory(
        config={"connections": [{"name": "foo"}, {"name": "FOO"}]}
    )
    with pytest.raises(
        ValueError,
        match="Duplicate connection names found after sanitize: 'FOO' and 'foo'",
    ):
        assert mock_bot.get_connection_configs() == {
            "foo": {
                "name": "FOO",
            },
        }


def test_no_instance_config(unset_bot) -> None:
    cloudbot.bot.bot_instance.set(None)
    with pytest.raises(ValueError):
        _ = cloudbot.bot.bot_instance.config


def test_deprecated_bot_var(unset_bot) -> None:
    with pytest.deprecated_call():
        _ = cloudbot.bot.bot.get()


@pytest.mark.asyncio()
async def test_migrate_db(
    mock_db, mock_bot_factory, mock_requests, tmp_path
) -> None:
    old_db_url = f"sqlite:///{tmp_path / 'database1.db'!s}"
    with MockDB(old_db_url, True) as old_db:
        table = Table(
            "foobar",
            database.metadata,
            Column("a", String, primary_key=True),
            Column("b", String, default="bar"),
        )

        other_table = Table(
            "foobar1",
            database.metadata,
            Column("a", String, primary_key=True),
            Column("b", String, default="bar"),
        )

        _ = Table(
            "foobar2",
            database.metadata,
            Column("a", String, primary_key=True),
            Column("b", String, default="bar"),
        )

        table.create(old_db.engine)
        other_table.create(old_db.engine)
        mock_bot = mock_bot_factory(
            db=mock_db,
            config={"old_database": old_db_url, "migrate_db": True},
        )

        mock_bot.do_db_migrate = True
        mock_bot.old_db = old_db_url

        old_db.add_row(table, a="blah")

        old_db.add_row(table, a="blah1", b="thing")

        old_db.add_row(table, a="blah2", b="thing2")

        assert old_db.get_data(table) == [
            ("blah", "bar"),
            ("blah1", "thing"),
            ("blah2", "thing2"),
        ]
        await CloudBot._init_routine(mock_bot)
        assert mock_db.get_data(table) == [
            ("blah", "bar"),
            ("blah1", "thing"),
            ("blah2", "thing2"),
        ]
        assert old_db.get_data(table) == []


@pytest.mark.asyncio()
async def test_connect_clients(mock_bot_factory) -> None:
    bot = mock_bot_factory()
    conn = MockClient(bot=bot)
    bot.connections = {"foo": conn}
    future = bot.loop.create_future()
    future.set_result(True)
    bot.plugin_manager.load_all = load_mock = MagicMock()
    load_mock.return_value = future
    await CloudBot._init_routine(bot)
    assert load_mock.mock_calls == [call(bot.base_dir / "plugins")]
    assert conn.mock_calls() == [call.try_connect()]


@pytest.mark.asyncio()
async def test_start_plugin_reload(tmp_path) -> None:
    bot = MagicMock(
        old_db=None,
        do_migrate_db=False,
    )

    bot.plugin_manager.load_all = AsyncMock()
    bot.running = True
    bot.plugin_reloading_enabled = True
    bot.config_reloading_enabled = True
    bot.connections = {}
    bot.plugin_dir = plugin_dir = tmp_path / "plugins"
    await CloudBot._init_routine(bot)
    assert bot.mock_calls == [
        call.plugin_manager.load_all(plugin_dir),
        call.plugin_reloader.start(str(plugin_dir)),
        call.config_reloader.start(),
        call.observer.start(),
    ]


class TestProcessing:
    @pytest.mark.asyncio()
    async def test_irc_catch_all(self, mock_bot_factory) -> None:
        bot = mock_bot_factory()
        conn = MockClient(bot=bot, nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )

        plugin = MagicMock()

        run_hooks = []

        @hook.irc_raw("*")
        async def coro(hook) -> None:
            run_hooks.append(hook)

        full_hook = RawHook(plugin, hook._get_hook(coro, "irc_raw"))
        bot.plugin_manager.catch_all_triggers.append(full_hook)

        await CloudBot.process(bot, event)
        assert sorted(run_hooks, key=id) == sorted(
            [
                full_hook,
            ],
            key=id,
        )

    @pytest.mark.asyncio()
    async def test_irc_catch_all_block(self, mock_bot_factory) -> None:
        bot = mock_bot_factory()
        conn = MockClient(bot=bot, nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )

        plugin = MagicMock()

        run_hooks = []

        @hook.irc_raw("*", action=Action.HALTTYPE, priority=Priority.HIGH)
        async def coro(hook) -> None:
            run_hooks.append(hook)

        @hook.irc_raw("*")
        async def coro1(hook) -> None:  # pragma: no cover
            run_hooks.append(hook)

        full_hook = RawHook(plugin, hook._get_hook(coro, "irc_raw"))
        full_hook1 = RawHook(plugin, hook._get_hook(coro1, "irc_raw"))
        bot.plugin_manager.catch_all_triggers.append(full_hook)
        bot.plugin_manager.catch_all_triggers.append(full_hook1)

        await CloudBot.process(bot, event)
        assert sorted(run_hooks, key=id) == sorted(
            [
                full_hook,
            ],
            key=id,
        )

    @pytest.mark.asyncio()
    async def test_command(self, mock_bot_factory) -> None:
        bot = mock_bot_factory()
        conn = MockClient(bot=bot, nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )

        plugin = MagicMock()

        run_hooks = []

        @hook.command("foo")
        async def coro(hook) -> None:
            run_hooks.append(hook)

        full_hook = CommandHook(plugin, hook._get_hook(coro, "command"))

        for cmd in full_hook.aliases:
            bot.plugin_manager.commands[cmd] = full_hook

        await CloudBot.process(bot, event)
        assert sorted(run_hooks, key=id) == sorted(
            [
                full_hook,
            ],
            key=id,
        )

    @pytest.mark.asyncio()
    async def test_command_partial(self, mock_bot_factory) -> None:
        bot = mock_bot_factory()
        conn = MockClient(bot=bot, nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )

        plugin = MagicMock()

        run_hooks = []

        @hook.command("foob", "fooc")
        async def coro(hook) -> None:  # pragma: no cover
            run_hooks.append(hook)

        full_hook = CommandHook(plugin, hook._get_hook(coro, "command"))

        for cmd in full_hook.aliases:
            bot.plugin_manager.commands[cmd] = full_hook

        await CloudBot.process(bot, event)
        assert sorted(run_hooks, key=id) == sorted(
            [],
            key=id,
        )

        assert conn.mock_calls() == [
            call.notice("bar", "Possible matches: foob or fooc"),
        ]

    @pytest.mark.asyncio()
    async def test_event(self, mock_bot_factory) -> None:
        bot = mock_bot_factory()
        conn = MockClient(bot=bot, nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )

        plugin = MagicMock()

        run_hooks = []

        @hook.event(EventType.message)
        async def coro(hook) -> None:
            run_hooks.append(hook)

        full_event_hook = EventHook(plugin, hook._get_hook(coro, "event"))
        for event_type in full_event_hook.types:
            bot.plugin_manager.event_type_hooks[event_type].append(
                full_event_hook
            )

        await CloudBot.process(bot, event)
        assert sorted(run_hooks, key=id) == sorted(
            [
                full_event_hook,
            ],
            key=id,
        )

    @pytest.mark.asyncio()
    async def test_event_block(self, mock_bot_factory, mock_db) -> None:
        bot = mock_bot_factory(db=mock_db)
        conn = MockClient(bot=bot, nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )

        plugin = MagicMock()

        run_hooks = []

        @hook.event(
            EventType.message, action=Action.HALTTYPE, priority=Priority.HIGH
        )
        async def coro(hook) -> None:
            run_hooks.append(hook)

        @hook.event(EventType.message)
        async def coro1(hook) -> None:  # pragma: no cover
            run_hooks.append(hook)

        full_event_hook = EventHook(plugin, hook._get_hook(coro, "event"))
        full_event_hook1 = EventHook(plugin, hook._get_hook(coro1, "event"))
        for event_type in full_event_hook.types:
            bot.plugin_manager.event_type_hooks[event_type].append(
                full_event_hook
            )

        for event_type in full_event_hook1.types:
            bot.plugin_manager.event_type_hooks[event_type].append(
                full_event_hook1
            )

        await CloudBot.process(bot, event)
        assert sorted(run_hooks, key=id) == sorted(
            [
                full_event_hook,
            ],
            key=id,
        )

    @pytest.mark.asyncio()
    async def test_irc_raw(self, mock_bot_factory) -> None:
        bot = mock_bot_factory()
        conn = MockClient(bot=bot, nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )

        plugin = MagicMock()

        run_hooks = []

        @hook.irc_raw("PRIVMSG")
        async def coro(hook) -> None:
            run_hooks.append(hook)

        full_hook = RawHook(plugin, hook._get_hook(coro, "irc_raw"))
        bot.plugin_manager.raw_triggers["PRIVMSG"].append(full_hook)
        await CloudBot.process(bot, event)
        assert sorted(run_hooks, key=id) == sorted(
            [
                full_hook,
            ],
            key=id,
        )

    @pytest.mark.asyncio()
    async def test_irc_raw_block(self, mock_bot_factory) -> None:
        bot = mock_bot_factory()
        conn = MockClient(bot=bot, nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )

        plugin = MagicMock()

        run_hooks = []

        @hook.irc_raw("PRIVMSG", priority=Priority.HIGH, action=Action.HALTTYPE)
        async def coro(hook) -> None:
            run_hooks.append(hook)

        @hook.irc_raw("PRIVMSG", priority=Priority.NORMAL)
        async def coro1(hook) -> None:  # pragma: no cover
            run_hooks.append(hook)

        full_hook = RawHook(plugin, hook._get_hook(coro, "irc_raw"))
        full_hook1 = RawHook(plugin, hook._get_hook(coro1, "irc_raw"))
        bot.plugin_manager.raw_triggers["PRIVMSG"].append(full_hook)
        bot.plugin_manager.raw_triggers["PRIVMSG"].append(full_hook1)

        await CloudBot.process(bot, event)
        assert sorted(run_hooks, key=id) == sorted(
            [
                full_hook,
            ],
            key=id,
        )


@pytest.mark.asyncio()
async def test_reload_config(mock_bot_factory) -> None:
    bot = mock_bot_factory()
    conn = MockClient(bot=bot)
    bot.connections = {"foo": conn}
    bot.config.load_config = MagicMock()
    runs = []

    @hook.config()
    @hook.config()
    async def coro(hook) -> None:
        runs.append(hook)

    plugin = MagicMock()
    config_hook = ConfigHook(plugin, hook._get_hook(coro, "config"))

    bot.plugin_manager.config_hooks.append(config_hook)

    bot.config.load_config.assert_not_called()
    await CloudBot.reload_config(bot)
    assert conn.mock_calls() == [call.reload()]
    bot.config.load_config.assert_called()
    assert runs == [config_hook]


@pytest.mark.parametrize(
    "text,result",
    (
        ("connection", "connection"),
        ("c onn ection", "c_onn_ection"),
        ("c+onn ection", "conn_ection"),
    ),
)
def test_clean_name(text, result) -> None:
    assert clean_name(text) == result


def test_get_cmd_regex(mock_bot) -> None:
    event = Event(
        channel="TestUser",
        nick="TestUser",
        conn=MockClient(bot=mock_bot, nick="Bot"),
    )
    regex = get_cmd_regex(event)
    expected = r"""
        ^
        # Prefix or nick
        (?:
            (?P<prefix>[\.])?
            |
            Bot[,;:]+\s+
        )
        (?P<command>\w+)  # Command
        (?:$|\s+)
        (?P<text>.*)     # Text
        """

    assert regex.pattern == expected


def patch_config(config):
    return patch("cloudbot.config.Config.load_config", new=config_mock(config))


def config_mock(config):
    def _load_config(self) -> None:
        self.update(config)

    return _load_config


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "config_enabled,plugin_enabled", list(product([True, False], [True, False]))
)
async def test_reloaders(
    tmp_path, config_enabled, plugin_enabled, unset_bot
) -> None:
    with patch_config(
        {
            "connections": [],
            "reloading": {
                "plugin_reloading": plugin_enabled,
                "config_reloading": config_enabled,
            },
        }
    ):
        bot = CloudBot(loop=asyncio.get_running_loop(), base_dir=tmp_path)
        assert bot.config_reloading_enabled is config_enabled
        assert bot.plugin_reloading_enabled is plugin_enabled
        bot.observer.stop()


@pytest.mark.asyncio
async def test_set_error(tmp_path, unset_bot) -> None:
    with patch_config(
        {
            "connections": [],
        }
    ):
        bot = CloudBot(loop=asyncio.get_running_loop(), base_dir=tmp_path)
        with pytest.raises(ValueError):
            CloudBot(loop=asyncio.get_running_loop(), base_dir=tmp_path)

        bot.observer.stop()


@pytest.mark.asyncio
async def test_load_clients(tmp_path, unset_bot, mock_db) -> None:
    with (
        patch_config(
            {
                "connections": [
                    {
                        "type": "irc",
                        "name": "foobar",
                        "nick": "TestBot",
                        "channels": [],
                        "connection": {"server": "irc.example.com"},
                    }
                ]
            }
        ),
        patch("cloudbot.bot.create_engine") as mock_create_engine,
    ):
        mock_create_engine.return_value = mock_db.engine
        (tmp_path / "data").mkdir(exist_ok=True, parents=True)
        bot = CloudBot(loop=asyncio.get_running_loop(), base_dir=tmp_path)
        conn = bot.connections["foobar"]
        assert conn.nick == "TestBot"
        assert conn.type == "irc"
        with pytest.deprecated_call():
            assert bot.data_dir == str(tmp_path / "data")

        bot.observer.stop()
