import asyncio
import ssl
from unittest.mock import MagicMock

import pytest

from cloudbot.clients.irc import IrcClient
from plugins.core import core_connect
from tests.util import test_data_dir


class MockClient(IrcClient):
    send = MagicMock()

    async def connect(self, timeout=None):
        pass


class MockBot:
    loop = asyncio.get_event_loop()
    repo_link = "https://github.com/foobar/baz"


def test_ssl_client():
    bot = MockBot()
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
                "client_cert": str(test_data_dir / "cloudbot.pem"),
            }
        },
    )

    assert client.use_ssl
    assert client.ssl_context

    assert client.ssl_context.check_hostname is True
    assert client.ssl_context.verify_mode is ssl.CERT_REQUIRED


def test_ssl_client_no_verify():
    bot = MockBot()
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
                "client_cert": str(test_data_dir / "cloudbot1.pem"),
            }
        },
    )

    assert client.use_ssl
    assert client.ssl_context

    assert client.ssl_context.check_hostname is False
    assert client.ssl_context.verify_mode is ssl.CERT_NONE


@pytest.mark.asyncio()
async def test_core_connects():
    bot = MockBot()
    config = {"connection": {"server": "example.com", "password": "foobar123"}}
    client = MockClient(bot, "mock", "foo", "FooBot", config=config,)
    assert client.type == "mock"

    await client.connect()

    core_connect.conn_pass(client)
    client.send.assert_called_with("PASS foobar123")
    core_connect.conn_nick(client)
    client.send.assert_called_with("NICK FooBot")
    core_connect.conn_user(client, bot)
    client.send.assert_called_with(
        "USER cloudbot 3 * :CloudBot - https://github.com/foobar/baz"
    )
