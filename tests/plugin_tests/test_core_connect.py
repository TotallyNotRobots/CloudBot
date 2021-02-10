import ssl
from unittest.mock import MagicMock

import pytest

from cloudbot.clients.irc import IrcClient


class MockClient(IrcClient):
    send = MagicMock()

    async def connect(self, timeout=None):
        pass


def test_ssl_client(event_loop, mock_bot_factory):
    bot = mock_bot_factory(loop=event_loop)
    client = MockClient(
        bot,
        "mock",
        "foo",
        "FooBot",
        config={
            "connection": {
                "server": "example.com",
                "password": "foobar123",
                "ssl": True,
                "client_cert": "tests/data/cloudbot.pem",
            }
        },
    )

    assert client.use_ssl
    assert client.ssl_context

    assert client.ssl_context.check_hostname is True
    assert client.ssl_context.verify_mode is ssl.CERT_REQUIRED


def test_ssl_client_no_verify(event_loop, mock_bot_factory):
    bot = mock_bot_factory(loop=event_loop)
    client = MockClient(
        bot,
        "mock",
        "foo",
        "FooBot",
        config={
            "connection": {
                "server": "example.com",
                "password": "foobar123",
                "ssl": True,
                "ignore_cert": True,
                "client_cert": "tests/data/cloudbot1.pem",
            }
        },
    )

    assert client.use_ssl
    assert client.ssl_context

    assert client.ssl_context.check_hostname is False
    assert client.ssl_context.verify_mode is ssl.CERT_NONE


@pytest.mark.asyncio()
async def test_core_connects(event_loop, mock_bot_factory):
    bot = mock_bot_factory(loop=event_loop)
    client = MockClient(
        bot,
        "mock",
        "foo",
        "FooBot",
        config={
            "connection": {"server": "example.com", "password": "foobar123"}
        },
    )
    assert client.type == "mock"

    await client.connect()

    from plugins.core.core_connect import conn_nick, conn_pass, conn_user

    conn_pass(client)
    client.send.assert_called_with("PASS foobar123")
    conn_nick(client)
    client.send.assert_called_with("NICK FooBot")
    conn_user(client, bot)
    client.send.assert_called_with(
        "USER cloudbot 3 * :CloudBot - https://github.com/foobar/baz"
    )
