import textwrap
from unittest.mock import MagicMock, call, patch

import pytest

from cloudbot import config, hook
from cloudbot.bot import CloudBot, clean_name, get_cmd_regex
from cloudbot.event import Event, EventType
from cloudbot.hook import Action, Priority
from cloudbot.plugin_hooks import CommandHook, ConfigHook, EventHook, RawHook
from tests.util.mock_bot import MockBot


@pytest.mark.asyncio()
async def test_connect_clients():
    bot = MockBot()
    conn = MockConn()
    bot.connections = {"foo": conn}
    future = bot.loop.create_future()
    future.set_result(True)
    conn.try_connect.return_value = future
    bot.plugin_manager.load_all = load_mock = MagicMock()
    load_mock.return_value = future
    await CloudBot._init_routine(bot)
    assert load_mock.mock_calls == [call(str(bot.base_dir / "plugins"))]
    conn.try_connect.assert_called()


class MockConn:
    def __init__(self, nick=None):
        self.nick = nick
        self.config = {}
        self.reload = MagicMock()
        self.try_connect = MagicMock()


class TestProcessing:
    @pytest.mark.asyncio()
    async def test_irc_catch_all(self) -> None:
        bot = MockBot()
        conn = MockConn(nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )
        event.notice = MagicMock()
        plugin = MagicMock()

        run_hooks = []

        @hook.irc_raw("*")
        async def coro(hook):
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
    async def test_irc_catch_all_block(self) -> None:
        bot = MockBot()
        conn = MockConn(nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )
        event.notice = MagicMock()
        plugin = MagicMock()

        run_hooks = []

        @hook.irc_raw("*", action=Action.HALTTYPE, priority=Priority.HIGH)
        async def coro(hook):
            run_hooks.append(hook)

        @hook.irc_raw("*")
        async def coro1(hook):  # pragma: no cover
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
    async def test_command(self) -> None:
        bot = MockBot()
        conn = MockConn(nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )
        event.notice = MagicMock()
        plugin = MagicMock()

        run_hooks = []

        @hook.command("foo")
        async def coro(hook):
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
    async def test_command_partial(self) -> None:
        bot = MockBot()
        conn = MockConn(nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )
        event.notice = MagicMock()
        plugin = MagicMock()

        run_hooks = []

        @hook.command("foob", "fooc")
        async def coro(hook):  # pragma: no cover
            run_hooks.append(hook)

        full_hook = CommandHook(plugin, hook._get_hook(coro, "command"))

        for cmd in full_hook.aliases:
            bot.plugin_manager.commands[cmd] = full_hook

        await CloudBot.process(bot, event)
        assert sorted(run_hooks, key=id) == sorted(
            [],
            key=id,
        )

        event.notice.assert_called_once_with("Possible matches: foob or fooc")

    @pytest.mark.asyncio()
    async def test_event(self) -> None:
        bot = MockBot()
        conn = MockConn(nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )
        event.notice = MagicMock()
        plugin = MagicMock()

        run_hooks = []

        @hook.event(EventType.message)
        async def coro(hook):
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
    async def test_event_block(self) -> None:
        bot = MockBot()
        conn = MockConn(nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )
        event.notice = MagicMock()
        plugin = MagicMock()

        run_hooks = []

        @hook.event(
            EventType.message, action=Action.HALTTYPE, priority=Priority.HIGH
        )
        async def coro(hook):
            run_hooks.append(hook)

        @hook.event(EventType.message)
        async def coro1(hook):  # pragma: no cover
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
    async def test_irc_raw(self) -> None:
        bot = MockBot()
        conn = MockConn(nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )
        event.notice = MagicMock()
        plugin = MagicMock()

        run_hooks = []

        @hook.irc_raw("PRIVMSG")
        async def coro(hook):
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
    async def test_irc_raw_block(self):
        bot = MockBot()
        conn = MockConn(nick="bot")
        event = Event(
            irc_command="PRIVMSG",
            event_type=EventType.message,
            channel="#foo",
            nick="bar",
            conn=conn,
            content=".foo bar",
        )
        event.notice = MagicMock()
        plugin = MagicMock()

        run_hooks = []

        @hook.irc_raw("PRIVMSG", priority=Priority.HIGH, action=Action.HALTTYPE)
        async def coro(hook):
            run_hooks.append(hook)

        @hook.irc_raw("PRIVMSG", priority=Priority.NORMAL)
        async def coro1(hook):  # pragma: no cover
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
async def test_reload_config():
    bot = MockBot()
    conn = MockConn()
    bot.connections = {"foo": conn}
    bot.config.load_config = MagicMock()
    runs = []

    @hook.config()
    @hook.config()
    async def coro(hook):
        runs.append(hook)

    plugin = MagicMock()
    config_hook = ConfigHook(plugin, hook._get_hook(coro, "config"))

    bot.plugin_manager.config_hooks.append(config_hook)

    bot.config.load_config.assert_not_called()
    await CloudBot.reload_config(bot)
    conn.reload.assert_called()
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
def test_clean_name(text, result):
    assert clean_name(text) == result


def test_get_cmd_regex():
    event = Event(channel="TestUser", nick="TestUser", conn=MockConn("Bot"))
    regex = get_cmd_regex(event)
    assert textwrap.dedent(regex.pattern) == textwrap.dedent(
        r"""
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
    )


class MockConfig(config.Config):
    def load_config(self):
        self.update(
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
        )


def test_load_clients():
    with patch("cloudbot.bot.Config", new=MockConfig):
        bot = CloudBot()
        conn = bot.connections["foobar"]
        assert conn.nick == "TestBot"
        assert conn.type == "irc"
