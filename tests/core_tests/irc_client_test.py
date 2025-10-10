import asyncio
from asyncio import CancelledError
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, call

import pytest

from cloudbot.client import ClientConnectError
from cloudbot.clients import irc
from cloudbot.event import Event, EventType
from tests.util.async_mock import AsyncMock

if TYPE_CHECKING:
    from asyncio import Future
    from typing import Tuple


def make_mock_conn(*, name="testconn"):
    loop = asyncio.get_running_loop()
    conn = MagicMock()
    conn.name = name
    conn.loop = loop
    conn.describe_server.return_value = "server.name:port"
    conn.auto_reconnect.return_value = asyncio.Future(loop=loop)

    return conn


def test_send_not_connected(mock_db):
    bot = MagicMock()
    client = irc.IrcClient(
        bot, "irc", "foo", "bar", config={"connection": {"server": "server"}}
    )

    with pytest.raises(ValueError):
        client.send("foobar")

    assert bot.mock_calls == [("loop.create_future", (), {})]


@pytest.mark.asyncio
async def test_send_closed(mock_db):
    bot = MagicMock(loop=asyncio.get_running_loop())
    client = irc.IrcClient(
        bot, "irc", "foo", "bar", config={"connection": {"server": "server"}}
    )
    proto = irc._IrcProtocol(client)
    client._protocol = proto
    proto._connected = False
    proto._connecting = False
    client._send("foobar")
    with pytest.raises(ValueError):
        await TestLineParsing.wait_tasks(client)


class TestLineParsing:
    @staticmethod
    async def wait_tasks(conn, cancel=False):
        current = asyncio.current_task()
        tasks = {t for t in asyncio.all_tasks() if t is not current}

        if cancel:
            for task in tasks:
                task.cancel()

        try:
            await asyncio.gather(*tasks)
        except CancelledError:
            if not cancel:
                raise  # pragma: no cover

    @staticmethod
    def _filter_event(event: Event) -> dict[str, Any]:
        return {k: v for k, v in dict(event).items() if not callable(v)}

    def make_proto(self):
        conn = make_mock_conn()
        conn.nick = "me"
        out = []

        async def func(e):
            out.append(self._filter_event(e))

        conn.bot.process = func

        proto = irc._IrcProtocol(conn)
        return conn, out, proto

    @pytest.mark.asyncio
    async def test_data_received(self, caplog_bot):
        conn, out, proto = self.make_proto()
        proto.data_received(
            b":server.host COMMAND this is :a command\r\n:server.host PRIVMSG me :hi\r\n"
        )

        await self.wait_tasks(conn)

        assert out == [
            {
                "irc_tags": None,
                "chan": "server.host",
                "content": None,
                "content_raw": None,
                "db": None,
                "db_executor": None,
                "hook": None,
                "host": "",
                "irc_command": "COMMAND",
                "irc_ctcp_text": None,
                "irc_paramlist": ["this", "is", "a command"],
                "irc_prefix": "server.host",
                "irc_raw": ":server.host COMMAND this is :a command",
                "mask": "server.host",
                "nick": "server.host",
                "target": None,
                "type": EventType.other,
                "user": "",
            },
            {
                "irc_tags": None,
                "chan": "server.host",
                "content": "hi",
                "content_raw": "hi",
                "db": None,
                "db_executor": None,
                "hook": None,
                "host": "",
                "irc_command": "PRIVMSG",
                "irc_ctcp_text": None,
                "irc_paramlist": ["me", "hi"],
                "irc_prefix": "server.host",
                "irc_raw": ":server.host PRIVMSG me :hi",
                "mask": "server.host",
                "nick": "server.host",
                "target": None,
                "type": EventType.message,
                "user": "",
            },
        ]

        assert caplog_bot.record_tuples == []
        assert conn.mock_calls == []

    @pytest.mark.asyncio
    async def test_broken_line_doesnt_interrupt(self, caplog_bot):
        conn, out, proto = self.make_proto()
        proto.data_received(
            b":server\2.host CMD this is :a command\r\nPRIVMSG\r\n:server.host PRIVMSG me :hi\r\n"
        )

        await self.wait_tasks(conn)

        assert out == [
            {
                "chan": "server\x02.host",
                "content": None,
                "content_raw": None,
                "db": None,
                "db_executor": None,
                "hook": None,
                "host": "",
                "irc_command": "CMD",
                "irc_ctcp_text": None,
                "irc_paramlist": ["this", "is", "a command"],
                "irc_prefix": "server\x02.host",
                "irc_raw": ":server\x02.host CMD this is :a command",
                "irc_tags": None,
                "mask": "server\x02.host",
                "nick": "server\x02.host",
                "target": None,
                "type": EventType.other,
                "user": "",
            },
            {
                "chan": "server.host",
                "content": "hi",
                "content_raw": "hi",
                "db": None,
                "db_executor": None,
                "hook": None,
                "host": "",
                "irc_command": "PRIVMSG",
                "irc_ctcp_text": None,
                "irc_paramlist": ["me", "hi"],
                "irc_prefix": "server.host",
                "irc_raw": ":server.host PRIVMSG me :hi",
                "irc_tags": None,
                "mask": "server.host",
                "nick": "server.host",
                "target": None,
                "type": EventType.message,
                "user": "",
            },
        ]
        assert caplog_bot.record_tuples == [
            (
                "cloudbot",
                40,
                "[testconn] Error occurred while parsing IRC line 'PRIVMSG' from "
                "server.name:port",
            )
        ]
        assert conn.mock_calls == [("describe_server", (), {})]

    @pytest.mark.asyncio
    async def test_pong(self, caplog_bot):
        conn, _, proto = self.make_proto()
        proto.data_received(b":server PING hi\r\n")

        conn.send.assert_called_with("PONG hi", log=False)
        await self.wait_tasks(conn, cancel=True)
        assert caplog_bot.record_tuples == []

    @pytest.mark.asyncio
    async def test_simple_cmd(self, caplog_bot):
        conn, _, proto = self.make_proto()
        event = proto.parse_line(":server.host COMMAND this is :a command")

        assert self._filter_event(event) == {
            "irc_tags": None,
            "chan": "server.host",
            "content": None,
            "content_raw": None,
            "db": None,
            "db_executor": None,
            "hook": None,
            "host": "",
            "irc_command": "COMMAND",
            "irc_ctcp_text": None,
            "irc_paramlist": ["this", "is", "a command"],
            "irc_prefix": "server.host",
            "irc_raw": ":server.host COMMAND this is :a command",
            "mask": "server.host",
            "nick": "server.host",
            "target": None,
            "type": EventType.other,
            "user": "",
        }
        assert caplog_bot.record_tuples == []
        assert conn.mock_calls == []

    @pytest.mark.asyncio
    async def test_parse_privmsg(self, caplog_bot):
        conn, _, proto = self.make_proto()
        event = proto.parse_line(
            ":sender!user@host PRIVMSG #channel :this is a message"
        )

        assert self._filter_event(event) == {
            "irc_tags": None,
            "chan": "#channel",
            "content": "this is a message",
            "content_raw": "this is a message",
            "db": None,
            "db_executor": None,
            "hook": None,
            "host": "host",
            "irc_command": "PRIVMSG",
            "irc_ctcp_text": None,
            "irc_paramlist": ["#channel", "this is a message"],
            "irc_prefix": "sender!user@host",
            "irc_raw": ":sender!user@host PRIVMSG #channel :this is a message",
            "mask": "sender!user@host",
            "nick": "sender",
            "target": None,
            "type": EventType.message,
            "user": "user",
        }
        assert caplog_bot.record_tuples == []
        assert conn.mock_calls == []

    @pytest.mark.asyncio
    async def test_parse_privmsg_ctcp_action(self, caplog_bot):
        conn, _, proto = self.make_proto()
        event = proto.parse_line(
            ":sender!user@host PRIVMSG #channel :\1ACTION this is an action\1"
        )

        assert self._filter_event(event) == {
            "irc_tags": None,
            "chan": "#channel",
            "content": "this is an action",
            "content_raw": "\x01ACTION this is an action\x01",
            "db": None,
            "db_executor": None,
            "hook": None,
            "host": "host",
            "irc_command": "PRIVMSG",
            "irc_ctcp_text": "ACTION this is an action",
            "irc_paramlist": ["#channel", "\x01ACTION this is an action\x01"],
            "irc_prefix": "sender!user@host",
            "irc_raw": ":sender!user@host PRIVMSG #channel :\x01ACTION this is an "
            "action\x01",
            "mask": "sender!user@host",
            "nick": "sender",
            "target": None,
            "type": EventType.action,
            "user": "user",
        }
        assert caplog_bot.record_tuples == []
        assert conn.mock_calls == []

    @pytest.mark.asyncio
    async def test_parse_privmsg_ctcp_version(self, caplog_bot):
        conn, _, proto = self.make_proto()
        event = proto.parse_line(
            ":sender!user@host PRIVMSG #channel :\1VERSION\1"
        )

        assert self._filter_event(event) == {
            "irc_tags": None,
            "chan": "#channel",
            "content": "\x01VERSION\x01",
            "content_raw": "\x01VERSION\x01",
            "db": None,
            "db_executor": None,
            "hook": None,
            "host": "host",
            "irc_command": "PRIVMSG",
            "irc_ctcp_text": "VERSION",
            "irc_paramlist": ["#channel", "\x01VERSION\x01"],
            "irc_prefix": "sender!user@host",
            "irc_raw": ":sender!user@host PRIVMSG #channel :\x01VERSION\x01",
            "mask": "sender!user@host",
            "nick": "sender",
            "target": None,
            "type": EventType.other,
            "user": "user",
        }
        assert caplog_bot.record_tuples == []
        assert conn.mock_calls == []

    @pytest.mark.asyncio
    async def test_parse_privmsg_bad_ctcp(self, caplog_bot):
        conn, _, proto = self.make_proto()
        event = proto.parse_line(
            ":sender!user@host PRIVMSG #channel :\1VERSION\1aa"
        )

        assert self._filter_event(event) == {
            "chan": "#channel",
            "content": "\x01VERSION\x01aa",
            "content_raw": "\x01VERSION\x01aa",
            "db": None,
            "db_executor": None,
            "hook": None,
            "host": "host",
            "irc_command": "PRIVMSG",
            "irc_ctcp_text": None,
            "irc_paramlist": ["#channel", "\x01VERSION\x01aa"],
            "irc_prefix": "sender!user@host",
            "irc_raw": ":sender!user@host PRIVMSG #channel :\x01VERSION\x01aa",
            "irc_tags": None,
            "mask": "sender!user@host",
            "nick": "sender",
            "target": None,
            "type": EventType.message,
            "user": "user",
        }
        assert caplog_bot.record_tuples == [
            (
                "cloudbot",
                10,
                "[testconn] Invalid CTCP message received, treating it as a mornal message",
            )
        ]
        assert conn.mock_calls == []

    @pytest.mark.asyncio
    async def test_parse_privmsg_format_reset(self, caplog_bot):
        conn, _, proto = self.make_proto()
        event = proto.parse_line(
            ":sender!user@host PRIVMSG #channel :\x02some text\x0faa"
        )

        assert self._filter_event(event) == {
            "chan": "#channel",
            "content": "\x02some text\x0faa",
            "content_raw": "\x02some text\x0faa",
            "db": None,
            "db_executor": None,
            "hook": None,
            "host": "host",
            "irc_command": "PRIVMSG",
            "irc_ctcp_text": None,
            "irc_paramlist": ["#channel", "\x02some text\x0faa"],
            "irc_prefix": "sender!user@host",
            "irc_raw": ":sender!user@host PRIVMSG #channel :\x02some text\x0faa",
            "irc_tags": None,
            "mask": "sender!user@host",
            "nick": "sender",
            "target": None,
            "type": EventType.message,
            "user": "user",
        }
        assert caplog_bot.record_tuples == []
        assert conn.mock_calls == []

    @pytest.mark.asyncio
    async def test_parse_no_prefix(self, caplog_bot):
        conn, _, proto = self.make_proto()
        event = proto.parse_line("SOMECMD thing")

        assert self._filter_event(event) == {
            "irc_tags": None,
            "chan": None,
            "content": None,
            "content_raw": None,
            "db": None,
            "db_executor": None,
            "hook": None,
            "host": None,
            "irc_command": "SOMECMD",
            "irc_ctcp_text": None,
            "irc_paramlist": ["thing"],
            "irc_prefix": None,
            "irc_raw": "SOMECMD thing",
            "mask": None,
            "nick": None,
            "target": None,
            "type": EventType.other,
            "user": None,
        }
        assert caplog_bot.record_tuples == []
        assert conn.mock_calls == []

    @pytest.mark.asyncio
    async def test_parse_pm_privmsg(self, caplog_bot):
        conn, _, proto = self.make_proto()
        event = proto.parse_line(
            ":sender!user@host PRIVMSG me :this is a message"
        )

        assert self._filter_event(event) == {
            "irc_tags": None,
            "chan": "sender",
            "content": "this is a message",
            "content_raw": "this is a message",
            "db": None,
            "db_executor": None,
            "hook": None,
            "host": "host",
            "irc_command": "PRIVMSG",
            "irc_ctcp_text": None,
            "irc_paramlist": ["me", "this is a message"],
            "irc_prefix": "sender!user@host",
            "irc_raw": ":sender!user@host PRIVMSG me :this is a message",
            "mask": "sender!user@host",
            "nick": "sender",
            "target": None,
            "type": EventType.message,
            "user": "user",
        }
        assert caplog_bot.record_tuples == []
        assert conn.mock_calls == []


class TestConnect:
    async def make_client(self) -> irc.IrcClient:
        bot = MagicMock(loop=asyncio.get_running_loop(), config={})
        conn_config = {
            "connection": {
                "server": "host.invalid",
                "timeout": 1,
                "bind_addr": "127.0.0.1",
                "bind_port": 0,
            }
        }
        client = irc.IrcClient(
            bot, "irc", "testconn", "foo", config=conn_config
        )
        client.active = True
        return client

    @pytest.mark.asyncio()
    async def test_exc(self, caplog_bot, mock_db):
        client = await self.make_client()
        runs = 0

        async def connect(timeout):
            nonlocal runs
            if runs == 5:
                return

            runs += 1
            raise OSError("foo")

        client.connect = connect  # type: ignore
        await client.try_connect()
        assert caplog_bot.record_tuples == [
            (
                "cloudbot",
                20,
                "[testconn|permissions] Created permission manager for testconn.",
            ),
            (
                "cloudbot",
                40,
                "[testconn] Error occurred while connecting to host.invalid:6667 (OSError: "
                "foo)",
            ),
            (
                "cloudbot",
                40,
                "[testconn] Error occurred while connecting to host.invalid:6667 (OSError: "
                "foo)",
            ),
            (
                "cloudbot",
                40,
                "[testconn] Error occurred while connecting to host.invalid:6667 (OSError: "
                "foo)",
            ),
            (
                "cloudbot",
                40,
                "[testconn] Error occurred while connecting to host.invalid:6667 (OSError: "
                "foo)",
            ),
            (
                "cloudbot",
                40,
                "[testconn] Error occurred while connecting to host.invalid:6667 (OSError: "
                "foo)",
            ),
        ]
        assert client.bot.mock_calls == []

    @pytest.mark.asyncio()
    async def test_timeout_exc(self, caplog_bot, mock_db):
        client = await self.make_client()
        runs = 0

        async def connect(timeout):
            nonlocal runs
            if runs == 5:
                return

            runs += 1
            raise TimeoutError("foo")

        client.connect = connect  # type: ignore
        await client.try_connect()
        assert caplog_bot.record_tuples == [
            (
                "cloudbot",
                20,
                "[testconn|permissions] Created permission manager for testconn.",
            ),
            (
                "cloudbot",
                40,
                "[testconn] Timeout occurred while connecting to host.invalid:6667",
            ),
            (
                "cloudbot",
                40,
                "[testconn] Timeout occurred while connecting to host.invalid:6667",
            ),
            (
                "cloudbot",
                40,
                "[testconn] Timeout occurred while connecting to host.invalid:6667",
            ),
            (
                "cloudbot",
                40,
                "[testconn] Timeout occurred while connecting to host.invalid:6667",
            ),
            (
                "cloudbot",
                40,
                "[testconn] Timeout occurred while connecting to host.invalid:6667",
            ),
        ]
        assert client.bot.mock_calls == []

    @pytest.mark.asyncio()
    async def test_other_exc(self, caplog_bot, mock_db):
        client = await self.make_client()

        client.connect = AsyncMock()  # type: ignore
        client.connect.side_effect = Exception("foo")

        with pytest.raises(ClientConnectError):
            await client.try_connect()

        assert caplog_bot.record_tuples == [
            (
                "cloudbot",
                20,
                "[testconn|permissions] Created permission manager for testconn.",
            ),
        ]
        assert client.bot.mock_calls == []

    @pytest.mark.asyncio()
    async def test_one_connect(self, caplog_bot, mock_db):
        client = await self.make_client()

        async def _connect(timeout=5):
            await asyncio.sleep(timeout)

        client._connect = _connect  # type: ignore
        with pytest.raises(
            ValueError,
            match="Attempted to connect while another connect attempt is happening",
        ):
            await asyncio.gather(client.connect(2), client.connect(0))

        assert caplog_bot.record_tuples == [
            (
                "cloudbot",
                20,
                "[testconn|permissions] Created permission manager for testconn.",
            ),
        ]
        assert client.bot.mock_calls == []

    @pytest.mark.asyncio()
    async def test_create_socket(self, caplog_bot, mock_db):
        client = await self.make_client()
        client.loop.create_connection = mock = MagicMock()
        fut: "Future[Tuple[None, None]]" = asyncio.Future(loop=client.loop)
        fut.set_result((None, None))
        mock.return_value = fut

        await client.connect()

        assert caplog_bot.record_tuples == [
            (
                "cloudbot",
                20,
                "[testconn|permissions] Created permission manager for testconn.",
            ),
            ("cloudbot", 20, "[testconn] Connecting"),
        ]
        assert client.bot.mock_calls == [
            ("plugin_manager.connect_hooks.__iter__", (), {})
        ]


class TestProtocol:
    @pytest.mark.asyncio
    async def test_connection_made(self, caplog_bot):
        conn = make_mock_conn()
        proto = irc._IrcProtocol(conn)
        transport = MagicMock()
        proto.connection_made(transport)

        assert proto._connected is True
        assert proto._connecting is False
        assert caplog_bot.record_tuples == []
        assert conn.mock_calls == []

    @pytest.mark.asyncio
    async def test_connection_lost(self, caplog_bot):
        conn = make_mock_conn()
        proto = irc._IrcProtocol(conn)
        proto._connected = True
        proto._connecting = True
        proto.connection_lost(None)

        assert proto._connected is False
        assert proto._connecting is True
        assert caplog_bot.record_tuples == []
        assert conn.mock_calls == [call.auto_reconnect()]


class TestSend:
    @pytest.mark.asyncio()
    async def test_send_sieve_error(self, caplog_bot):
        conn = make_mock_conn()
        proto = irc._IrcProtocol(conn)
        proto.connection_made(MagicMock())
        sieve = object()
        proto.bot.plugin_manager.out_sieves = [sieve]
        proto.bot.plugin_manager.internal_launch = launch = MagicMock()
        fut = proto.loop.create_future()
        fut.set_result((False, None))
        launch.return_value = fut

        await proto.send("PRIVMSG #foo bar")
        assert len(launch.mock_calls) == 1
        assert launch.mock_calls[0][1][0] is sieve

        assert caplog_bot.record_tuples == [
            (
                "cloudbot",
                30,
                "Error occurred in outgoing sieve, falling back to old behavior",
            ),
            ("cloudbot", 10, "Line was: PRIVMSG #foo bar"),
            ("cloudbot", 10, "[testconn|out] >> b'PRIVMSG #foo bar\\r\\n'"),
        ]
