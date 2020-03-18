import asyncio
import ssl
from unittest.mock import MagicMock

from cloudbot.clients.irc import IrcClient


class MockClient(IrcClient):
    send = MagicMock()

    def connect(self, timeout=None):
        pass


class MockBot:
    loop = asyncio.get_event_loop()


def test_ssl_client():
    bot = MockBot()
    client = MockClient(bot, 'mock', 'foo', 'FooBot', config={
        'connection': {
            'server': 'example.com',
            'password': 'foobar123',
            'ssl': True,
            'client_cert': 'tests/data/cloudbot.pem'
        }
    })

    assert client.use_ssl
    assert client.ssl_context

    assert client.ssl_context.check_hostname is True
    assert client.ssl_context.verify_mode is ssl.CERT_REQUIRED


def test_ssl_client_no_verify():
    bot = MockBot()
    client = MockClient(bot, 'mock', 'foo', 'FooBot', config={
        'connection': {
            'server': 'example.com',
            'password': 'foobar123',
            'ssl': True,
            'ignore_cert': True,
            'client_cert': 'tests/data/cloudbot1.pem'
        }
    })

    assert client.use_ssl
    assert client.ssl_context

    assert client.ssl_context.check_hostname is False
    assert client.ssl_context.verify_mode is ssl.CERT_NONE


def test_core_connects():
    bot = MockBot()
    client = MockClient(bot, 'mock', 'foo', 'FooBot', config={
        'connection': {
            'server': 'example.com',
            'password': 'foobar123'
        }
    })
    assert client.type == 'mock'

    client.connect()

    from plugins.core.core_connect import conn_pass, conn_nick, conn_user
    conn_pass(client)
    client.send.assert_called_with('PASS foobar123')
    conn_nick(client)
    client.send.assert_called_with('NICK FooBot')
    conn_user(client)
    client.send.assert_called_with('USER cloudbot 3 * :CloudBot - https://git.io/CloudBot')
