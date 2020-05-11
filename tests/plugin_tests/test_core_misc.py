import asyncio
from unittest.mock import MagicMock

import pytest

from cloudbot.client import Client

pytestmark = pytest.mark.asyncio


class Bot(MagicMock):
    loop = asyncio.get_event_loop()


class MockClient(Client):  # pylint: disable=abstract-method
    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, 'TestClient', *args, **kwargs)
        self.active = True

    join = MagicMock()


async def test_do_joins():
    client = MockClient(
        Bot(), 'foo', 'foobot', channels=['#foo']
    )
    from plugins.core import core_misc
    client.ready = True
    client.config['join_throttle'] = 0

    await core_misc.do_joins(client)

    client.join.assert_called_once_with('#foo')
