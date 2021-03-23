from typing import cast
from unittest.mock import MagicMock, call

import pytest

from cloudbot.client import Client
from plugins.core import core_misc


class MockClient(Client):  # pylint: disable=abstract-method
    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, "TestClient", *args, **kwargs)
        self.active = True
        self.join = MagicMock()  # type: ignore[assignment]


@pytest.mark.asyncio
async def test_do_joins(mock_bot_factory, event_loop):
    client = MockClient(
        mock_bot_factory(loop=event_loop),
        "foo",
        "foobot",
        channels=[
            "#foo",
            "#bar key",
            ["#baz", "key1"],
            {"name": "#chan"},
            {"name": "#chan1", "key": "key2"},
        ],
    )

    client.ready = True
    client.config["join_throttle"] = 0

    await core_misc.do_joins(client)

    assert cast(MagicMock, client.join).mock_calls == [
        call("#foo", None),
        call("#bar", "key"),
        call("#baz", "key1"),
        call("#chan", None),
        call("#chan1", "key2"),
    ]
