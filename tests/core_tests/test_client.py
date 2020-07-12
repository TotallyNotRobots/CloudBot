import asyncio
from unittest.mock import MagicMock, patch

import pytest

from cloudbot.client import Client, ClientConnectError


class Bot(MagicMock):
    loop = asyncio.get_event_loop()


class MockClient(Client):  # pylint: disable=abstract-method
    _connected = False

    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, "TestClient", *args, **kwargs)
        self.active = True

    @property
    def connected(self):
        return self._connected

    async def connect(self, timeout=None):
        self._connected = True

    def describe_server(self):
        return "MockServer"


class FailingMockClient(MockClient):  # pylint: disable=abstract-method
    async def connect(self, timeout=None):
        self.active = False
        raise ValueError("This is a test")


def test_client_no_config():
    client = MockClient(Bot(), "foo", "foobot", channels=["#foo"])
    assert client.config.get("a") is None


@pytest.mark.asyncio
async def test_client():
    client = MockClient(
        Bot(), "foo", "foobot", channels=["#foo"], config={"name": "foo"}
    )

    assert client.config_channels == ["#foo"]
    assert client.config["name"] == "foo"
    assert client.type == "TestClient"

    assert client.active is True
    client.active = False
    assert client.active is False
    client.active = True

    await client.try_connect()


@pytest.mark.asyncio
async def test_client_connect_exc():
    with pytest.raises(ClientConnectError):
        with patch("random.randrange", return_value=1):
            client = FailingMockClient(
                Bot(),
                "foo",
                "foobot",
                channels=["#foo"],
                config={"name": "foo"},
            )
            await client.try_connect()


@pytest.mark.asyncio
async def test_client_connect_inactive():
    with patch("random.randrange", return_value=1):
        client = FailingMockClient(
            Bot(), "foo", "foobot", channels=["#foo"], config={"name": "foo"}
        )
        client.active = False
        await client.try_connect()


@pytest.mark.asyncio
async def test_auto_reconnect():
    client = MockClient(
        Bot(), "foo", "foobot", channels=["#foo"], config={"name": "foo"}
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
