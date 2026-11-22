from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

from typing_extensions import override

from cloudbot.client import Client

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from unittest.mock import _CallList

    from cloudbot.bot import AbstractBot
    from cloudbot.config import ConfigChannelList
    from cloudbot.permissions import PermissionManager


class MockClient(Client):
    def __init__(
        self,
        *,
        bot: AbstractBot,
        nick: str | None = None,
        name: str | None = None,
        config: dict[str, Any] | None = None,
        channels: ConfigChannelList | None = None,
        connected: bool = True,
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
        self._client: Client = cast("Client", self._mock)
        self.active = True
        self.ready: bool = connected
        self._connected: bool = connected

    @property
    @override
    def connected(self) -> bool:
        return self._connected

    @connected.setter
    def connected(self, value: bool) -> None:
        self._connected = value

    @override
    def reload(self) -> None:
        self._client.reload()

    @override
    async def try_connect(self) -> None:
        self._connected = True
        await self._client.try_connect()

    @override
    async def connect(self, timeout: float | None = None) -> None:
        self._connected = True
        await self._client.connect(timeout=timeout)

    @override
    def join(self, channel: str, key: str | None = None) -> None:
        self._client.join(channel, key)

    @override
    def notice(self, target: str, text: str) -> None:
        self._client.notice(target, text)

    @override
    def is_nick_valid(self, nick: str) -> bool:
        return True

    def mock_calls(self) -> _CallList:
        return self._mock.mock_calls


class MockConn:
    def __init__(
        self,
        *,
        nick: str | None = None,
        name: str | None = None,
        loop: AbstractEventLoop | None = None,
    ) -> None:
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

    def is_nick_valid(self, nick: str) -> bool:
        return True
