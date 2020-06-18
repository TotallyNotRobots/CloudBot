import asyncio
import logging
import socket
from asyncio import Task
from unittest.mock import MagicMock, call, patch

import pytest

import cloudbot.clients.irc as irc
from cloudbot.client import ClientConnectError
from cloudbot.event import EventType
from cloudbot.util import async_util


class TestLineParsing:
    def _filter_event(self, event):
        return {k: v for k, v in dict(event).items() if not callable(v)}

    def test_data_received(self):
        conn, out, proto = self.make_proto()
        proto.data_received(
            b":server.host COMMAND this is :a command\r\n:server.host PRIVMSG me :hi\r\n"
        )

        conn.loop.run_until_complete(asyncio.gather(*Task.all_tasks(conn.loop)))

        assert out == [
            {
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

    def make_proto(self):
        conn = MagicMock()
        conn.nick = "me"
        conn.loop = asyncio.get_event_loop_policy().new_event_loop()
        out = []

        async def func(e):
            out.append(self._filter_event(e))

        conn.bot.process = func
        proto = irc._IrcProtocol(conn)
        return conn, out, proto

    def test_broken_line_doesnt_interrupt(self):
        conn, out, proto = self.make_proto()
        proto.data_received(
            b":server.host COMMAND this is :a command\r\nPRIVMSG\r\n:server.host PRIVMSG me :hi\r\n"
        )

        conn.loop.run_until_complete(asyncio.gather(*Task.all_tasks(conn.loop)))

        assert out == [
            {
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

    def test_pong(self):
        conn, _, proto = self.make_proto()
        proto.data_received(b":server PING hi\r\n")

        conn.send.assert_called_with("PONG hi", log=False)

    def test_simple_cmd(self):
        _, _, proto = self.make_proto()
        event = proto.parse_line(":server.host COMMAND this is :a command")

        assert self._filter_event(event) == {
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

    def test_parse_privmsg(self):
        _, _, proto = self.make_proto()
        event = proto.parse_line(
            ":sender!user@host PRIVMSG #channel :this is a message"
        )

        assert self._filter_event(event) == {
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

    def test_parse_privmsg_ctcp_action(self):
        _, _, proto = self.make_proto()
        event = proto.parse_line(
            ":sender!user@host PRIVMSG #channel :\1ACTION this is an action\1"
        )

        assert self._filter_event(event) == {
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

    def test_parse_privmsg_ctcp_version(self):
        _, _, proto = self.make_proto()
        event = proto.parse_line(":sender!user@host PRIVMSG #channel :\1VERSION\1")

        assert self._filter_event(event) == {
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

    def test_parse_privmsg_bad_ctcp(self):
        _, _, proto = self.make_proto()
        event = proto.parse_line(":sender!user@host PRIVMSG #channel :\1VERSION\1aa")

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
            "mask": "sender!user@host",
            "nick": "sender",
            "target": None,
            "type": EventType.message,
            "user": "user",
        }

    def test_parse_no_prefix(self):
        _, _, proto = self.make_proto()
        event = proto.parse_line("SOMECMD thing")

        assert self._filter_event(event) == {
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

    def test_parse_pm_privmsg(self):
        _, _, proto = self.make_proto()
        event = proto.parse_line(":sender!user@host PRIVMSG me :this is a message")

        assert self._filter_event(event) == {
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


@pytest.fixture()
def patch_logger():
    with patch.object(irc.logger, "isEnabledFor") as enabled:
        enabled.return_value = True
        with patch.object(irc.logger, "_log") as mock_log:
            yield mock_log


class TestConnect:
    async def make_client(self) -> irc.IrcClient:
        bot = MagicMock(loop=asyncio.get_event_loop(), config={})
        conn_config = {
            "connection": {
                "server": "host.invalid",
                "timeout": 1,
                "bind_addr": "127.0.0.1",
                "bind_port": 0,
            }
        }
        client = irc.IrcClient(bot, "irc", "testconn", "foo", config=conn_config)
        client.active = True
        return client

    @pytest.mark.asyncio()
    async def test_exc(self, patch_logger):
        client = await self.make_client()
        runs = 0

        # noinspection PyUnusedLocal
        async def connect(timeout):
            nonlocal runs
            if runs == 5:
                return

            runs += 1
            raise socket.error("foo")

        client.connect = connect
        await client.try_connect()
        assert patch_logger.mock_calls == [
            call(
                logging.INFO,
                "[%s|permissions] Created permission manager for %s.",
                ("testconn", "testconn"),
            ),
            call(
                logging.INFO,
                "[%s|permissions] Reloading permissions for %s.",
                ("testconn", "testconn"),
            ),
            call(
                logging.DEBUG,
                "[%s|permissions] Group permissions: %s",
                ("testconn", {}),
            ),
            call(logging.DEBUG, "[%s|permissions] Group users: %s", ("testconn", {})),
            call(
                logging.DEBUG, "[%s|permissions] Permission users: %s", ("testconn", {})
            ),
            call(
                logging.ERROR,
                "[%s] Error occurred while connecting to %s (%s)",
                ("testconn", "host.invalid:6667", "OSError: foo"),
            ),
            call(
                logging.ERROR,
                "[%s] Error occurred while connecting to %s (%s)",
                ("testconn", "host.invalid:6667", "OSError: foo"),
            ),
            call(
                logging.ERROR,
                "[%s] Error occurred while connecting to %s (%s)",
                ("testconn", "host.invalid:6667", "OSError: foo"),
            ),
            call(
                logging.ERROR,
                "[%s] Error occurred while connecting to %s (%s)",
                ("testconn", "host.invalid:6667", "OSError: foo"),
            ),
            call(
                logging.ERROR,
                "[%s] Error occurred while connecting to %s (%s)",
                ("testconn", "host.invalid:6667", "OSError: foo"),
            ),
        ]

    @pytest.mark.asyncio()
    async def test_timeout_exc(self, patch_logger):
        client = await self.make_client()
        runs = 0

        # noinspection PyUnusedLocal
        async def connect(timeout):
            nonlocal runs
            if runs == 5:
                return

            runs += 1
            raise TimeoutError("foo")

        client.connect = connect
        await client.try_connect()
        assert patch_logger.mock_calls == [
            call(
                20,
                "[%s|permissions] Created permission manager for %s.",
                ("testconn", "testconn"),
            ),
            call(
                20,
                "[%s|permissions] Reloading permissions for %s.",
                ("testconn", "testconn"),
            ),
            call(10, "[%s|permissions] Group permissions: %s", ("testconn", {})),
            call(10, "[%s|permissions] Group users: %s", ("testconn", {})),
            call(10, "[%s|permissions] Permission users: %s", ("testconn", {})),
            call(
                40,
                "[%s] Timeout occurred while connecting to %s",
                ("testconn", "host.invalid:6667"),
            ),
            call(
                40,
                "[%s] Timeout occurred while connecting to %s",
                ("testconn", "host.invalid:6667"),
            ),
            call(
                40,
                "[%s] Timeout occurred while connecting to %s",
                ("testconn", "host.invalid:6667"),
            ),
            call(
                40,
                "[%s] Timeout occurred while connecting to %s",
                ("testconn", "host.invalid:6667"),
            ),
            call(
                40,
                "[%s] Timeout occurred while connecting to %s",
                ("testconn", "host.invalid:6667"),
            ),
        ]

    @pytest.mark.asyncio()
    async def test_other_exc(self, patch_logger):
        client = await self.make_client()

        # noinspection PyUnusedLocal
        async def connect(timeout):
            raise Exception("foo")

        client.connect = connect
        with pytest.raises(ClientConnectError):
            await client.try_connect()

        assert patch_logger.mock_calls == [
            call(
                20,
                "[%s|permissions] Created permission manager for %s.",
                ("testconn", "testconn"),
            ),
            call(
                20,
                "[%s|permissions] Reloading permissions for %s.",
                ("testconn", "testconn"),
            ),
            call(10, "[%s|permissions] Group permissions: %s", ("testconn", {})),
            call(10, "[%s|permissions] Group users: %s", ("testconn", {})),
            call(10, "[%s|permissions] Permission users: %s", ("testconn", {})),
        ]

    @pytest.mark.asyncio()
    async def test_one_connect(self):
        client = await self.make_client()

        async def _connect(timeout):
            await asyncio.sleep(timeout)

        client._connect = _connect
        with pytest.raises(
            ValueError,
            match="Attempted to connect while another connect attempt is happening",
        ):
            await asyncio.gather(client.connect(2), client.connect(0))

    @pytest.mark.asyncio()
    async def test_create_socket(self):
        client = await self.make_client()
        client.loop.create_connection = mock = MagicMock()
        fut = asyncio.Future(loop=client.loop)
        fut.set_result((None, None))
        mock.return_value = fut

        await client.connect()


class TestSend:
    @pytest.mark.asyncio()
    async def test_send_sieve_error(self):
        proto = irc._IrcProtocol(MagicMock(loop=asyncio.get_event_loop()))
        proto._connected = True
        proto._transport = MagicMock()
        sieve = object()
        proto.bot.plugin_manager.out_sieves = [sieve]
        proto.bot.plugin_manager.internal_launch = launch = MagicMock()
        fut = async_util.create_future(proto.loop)
        fut.set_result((False, None))
        launch.return_value = fut

        await proto.send("PRIVMSG #foo bar")
        assert len(launch.mock_calls) == 1
        assert launch.mock_calls[0][1][0] is sieve
