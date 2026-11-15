from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

from cloudbot.client import Client

if TYPE_CHECKING:
    from unittest.mock import _CallList

    from cloudbot.bot import AbstractBot
    from cloudbot.permissions import PermissionManager


class MockClient(Client):
    def __init__(
        self,
        *,
        bot: AbstractBot,
        nick=None,
        name=None,
        config=None,
        channels=None,
        connected=True,
    ) -> None:
        super().__init__(
            bot=bot,
            _type="mock",
            name=name or "testconn",
            nick=nick or "TestBot",
            config=config or {},
            channels=channels,
        )
        self._mock = MagicMock(spec=Client)
        self.active = True
        self.ready = connected
        self._connected = connected

    @property
    def connected(self) -> bool:
        return self._connected

    @connected.setter
    def connected(self, value) -> None:
        self._connected = value

    def reload(self):
        return self._mock.reload()

    async def try_connect(self):
        self._connected = True
        return await self._mock.try_connect()

    async def connect(self, timeout=None):  # noqa: ASYNC109 # TODO: Replace timeout logic with asyncio.timeout
        self._connected = True
        return await self._mock.connect(timeout=timeout)

    def join(self, channel, key=None):
        return self._mock.join(channel, key)

    def notice(self, target, text):
        return self._mock.notice(target, text)

    def is_nick_valid(self, nick) -> bool:
        return True

    def mock_calls(self) -> _CallList:
        return self._mock.mock_calls


class MockConn:
    def __init__(self, *, nick=None, name=None, loop=None) -> None:
        self.nick = nick or "TestBot"
        self.name = name or "testconn"
        self.permissions: PermissionManager | None = None
        self.config: dict[str, Any] = {}
        self.history: dict[str, list[tuple[str, float, str]]] = {}
        self.reload = MagicMock()
        self.try_connect = MagicMock()
        self.notice = MagicMock()
        self.join = MagicMock()
        self.loop = loop
        self.ready = True

    def is_nick_valid(self, nick) -> bool:
        return True
