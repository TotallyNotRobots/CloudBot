from unittest.mock import MagicMock, _CallList

from cloudbot.bot import AbstractBot
from cloudbot.client import Client


class MockClient(Client):
    def __init__(self, *, bot: "AbstractBot", nick=None, name=None):
        super().__init__(
            bot=bot,
            _type="mock",
            name=name or "testconn",
            nick=nick or "TestBot",
        )
        self._mock = MagicMock(spec=Client)

    def reload(self):
        return self._mock.reload()

    async def try_connect(self):
        return self._mock.try_connect()

    def join(self, channel, key=None):
        return self._mock.join(channel, key)

    def notice(self, target, text):
        return self._mock.notice(target, text)

    def is_nick_valid(self, nick):
        return True

    def mock_calls(self) -> _CallList:
        return self._mock.mock_calls


class MockConn:
    def __init__(self, *, nick=None, name=None, loop=None):
        self.nick = nick or "TestBot"
        self.name = name or "testconn"
        self.permissions = None
        self.config = {}
        self.history = {}
        self.reload = MagicMock()
        self.try_connect = MagicMock()
        self.notice = MagicMock()
        self.join = MagicMock()
        self.loop = loop
        self.ready = True

    def is_nick_valid(self, nick):
        return True
