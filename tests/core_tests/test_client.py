from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from typing_extensions import override

from cloudbot.client import Client
from tests.util.mock_conn import MockClient

if TYPE_CHECKING:
    from cloudbot.bot import AbstractBot
    from cloudbot.config import ConfigChannelList
    from tests.util.mock_bot import MockBotFactory
    from tests.util.mock_db import MockDB


class FailingMockClient(MockClient):
    def __init__(
        self,
        *,
        bot: AbstractBot,
        nick: str | None = None,
        name: str | None = None,
        channels: ConfigChannelList | None = None,
        config: dict[str, Any] | None = None,
        fail_count: int | None = None,
    ) -> None:
        super().__init__(
            bot=bot, nick=nick, name=name, channels=channels, config=config
        )
        self.fail_count: int | None = fail_count

    @override
    async def connect(self, timeout: float | None = None) -> None:
        if self.fail_count is not None and self.fail_count > 0:
            self.fail_count -= 1
            raise ValueError("This is a test")


@pytest.mark.asyncio
async def test_reload(
    mock_bot_factory: MockBotFactory, mock_db: MockDB
) -> None:
    client = MockClient(
        bot=mock_bot_factory(db=mock_db),
        name="foo",
        nick="foobot",
        channels=["#foo"],
    )
    client.permissions = MagicMock()
    Client.reload(client)
    assert client.permissions.mock_calls == [("reload",)]


@pytest.mark.asyncio
async def test_client_no_config(
    mock_bot_factory: MockBotFactory, mock_db: MockDB
) -> None:
    client = MockClient(
        bot=mock_bot_factory(db=mock_db),
        name="foo",
        nick="foobot",
        channels=["#foo"],
    )
    assert client.config.get("a") is None


@pytest.mark.asyncio
async def test_client(
    mock_bot_factory: MockBotFactory, mock_db: MockDB
) -> None:
    client = MockClient(
        bot=mock_bot_factory(db=mock_db),
        name="foo",
        nick="foobot",
        channels=["#foo"],
        config={"name": "foo"},
    )

    assert client.config_channels == ["#foo"]
    assert client.config["name"] == "foo"
    assert client.type == "mock"

    assert client.active is True
    client.active = False
    assert client.active is False
    client.active = True

    await client.try_connect()


@pytest.mark.asyncio
async def test_client_connect_exc(
    mock_bot_factory: MockBotFactory, mock_db: MockDB
) -> None:
    with patch("random.randrange", return_value=1):
        client = FailingMockClient(
            bot=mock_bot_factory(db=mock_db),
            name="foo",
            nick="foobot",
            channels=["#foo"],
            config={"name": "foo"},
            fail_count=1,
        )
        await client.try_connect()


@pytest.mark.asyncio
async def test_try_connect(
    mock_bot_factory: MockBotFactory, mock_db: MockDB
) -> None:
    client = MockClient(
        bot=mock_bot_factory(db=mock_db),
        name="foo",
        nick="foobot",
        channels=["#foo"],
        config={"name": "foo"},
    )

    client.active = True
    await client.try_connect()


@pytest.mark.asyncio
async def test_auto_reconnect(
    mock_bot_factory: MockBotFactory, mock_db: MockDB
) -> None:
    client = MockClient(
        bot=mock_bot_factory(db=mock_db),
        name="foo",
        nick="foobot",
        channels=["#foo"],
        config={"name": "foo"},
        connected=False,
    )

    client.active = False
    assert client.active is False
    assert client.connected is False
    await client.auto_reconnect()
    assert client.connected is False

    client.active = True
    assert client.active is True
    assert client.connected is False
    await client.auto_reconnect()
    assert client.connected is True
