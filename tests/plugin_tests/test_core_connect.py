import ssl
from unittest.mock import call

import pytest

from plugins.core import core_connect
from tests.util.mock_irc_client import MockIrcClient


@pytest.mark.asyncio
async def test_ssl_client(mock_bot_factory, mock_db) -> None:
    bot = mock_bot_factory(db=mock_db)
    client = MockIrcClient(
        bot=bot,
        name="foo",
        nick="FooBot",
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


@pytest.mark.asyncio
async def test_ssl_client_no_verify(mock_bot_factory, mock_db) -> None:
    bot = mock_bot_factory(db=mock_db)
    client = MockIrcClient(
        bot=bot,
        name="foo",
        nick="FooBot",
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
async def test_core_connects(mock_bot_factory, mock_db) -> None:
    bot = mock_bot_factory(db=mock_db)
    client = MockIrcClient(
        bot=bot,
        name="foo",
        nick="FooBot",
        config={
            "connection": {"server": "example.com", "password": "foobar123"}
        },
    )
    assert client.type == "irc"

    await client.connect()

    core_connect.conn_pass(client)
    core_connect.conn_nick(client)
    core_connect.conn_user(client, bot)

    assert client.mock_calls() == [
        call.connect(timeout=None),
        call.send("PASS foobar123", True),
        call.send("NICK FooBot", True),
        call.send(
            "USER cloudbot 3 * :CloudBot - https://github.com/foobar/baz", True
        ),
    ]
