from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import MagicMock

from typing_extensions import override

from cloudbot.clients.irc import IrcClient

if TYPE_CHECKING:
    from unittest.mock import _CallList

    from cloudbot.bot import AbstractBot


class MockIrcClient(IrcClient):
    def __init__(
        self,
        *,
        bot: AbstractBot,
        nick: str | None = None,
        name: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        config = config or {}
        config.setdefault("connection", {}).setdefault("server", "foo.invalid")  # pyright: ignore[reportAny] # TODO: type config
        super().__init__(
            bot=bot,
            _type="irc",
            name=name or "testconn",
            nick=nick or "TestBot",
            config=config,
        )
        self._mock = MagicMock(spec=IrcClient)
        self._client: IrcClient = cast("IrcClient", self._mock)
        self.ready = True
        self.active = True

    @property
    def connected(self) -> bool:
        return True

    def reload(self) -> None:
        self._client.reload()

    async def try_connect(self) -> None:
        await self._client.try_connect()

    def is_nick_valid(self, nick: str | None) -> bool:
        return True

    @override
    async def connect(self, timeout: float | None = None) -> None:
        await self._client.connect(timeout=timeout)

    def send(self, line: str, log: bool = True) -> None:
        self._client.send(line, log)

    def mock_calls(self) -> _CallList:
        return self._mock.mock_calls
