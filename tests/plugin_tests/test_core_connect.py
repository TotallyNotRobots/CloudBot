import asyncio

from mock import MagicMock

from cloudbot.clients.irc import IrcClient


class MockClient(IrcClient):
    send = MagicMock()

    def connect(self, timeout=None):
        pass


class MockBot:
    loop = asyncio.get_event_loop()


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
