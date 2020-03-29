import asyncio
from unittest.mock import MagicMock

import pytest

from cloudbot.event import CommandEvent
from cloudbot.util import async_util
from plugins import admin_bot


@pytest.mark.asyncio
@pytest.mark.parametrize('input_text,chan,key', [
    ('#channel key', '#channel', 'key'),
    ('channel key', '#channel', 'key'),
    ('#channel', '#channel', None),
    ('channel', '#channel', None),
])
async def test_join(input_text, chan, key):
    conn = MagicMock()
    conn.config = {}
    conn.bot = None

    event = CommandEvent(
        text=input_text,
        cmd_prefix='.',
        triggered_command='join',
        hook=MagicMock(),
        bot=conn.bot,
        conn=conn,
        channel='#foo',
        nick='foobaruser',
    )

    await async_util.run_func_with_args(asyncio.get_event_loop(), admin_bot.join, event)

    event.conn.join.assert_called_with(chan, key)
