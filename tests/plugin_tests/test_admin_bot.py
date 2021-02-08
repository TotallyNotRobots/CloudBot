from unittest.mock import MagicMock, call

import pytest

from cloudbot.event import CommandEvent
from cloudbot.util import async_util, func_utils
from plugins import admin_bot


@pytest.mark.parametrize(
    "chan,text,result",
    [
        ("#foo", "bar", ("#foo", "bar")),
        ("#foo", "#bar baz", ("#bar", "baz")),
    ],
)
def test_get_chan(chan, text, result):
    assert admin_bot.get_chan(chan, text) == result


@pytest.mark.parametrize(
    "text,chan,out",
    [
        ("foo", "#bar", ["foo"]),
        ("", "#bar", ["#bar"]),
        ("foo baz", "#bar", ["foo", "baz"]),
    ],
)
def test_parse_targets(text, chan, out):
    assert admin_bot.parse_targets(text, chan) == out


@pytest.mark.asyncio
async def test_reload_config(event_loop):
    bot = MagicMock()
    future = event_loop.create_future()
    bot.reload_config.return_value = future
    future.set_result(True)
    res = await admin_bot.rehash_config(bot)
    assert res == "Config reloaded."
    assert bot.mock_calls == [call.reload_config()]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_text,chan,key",
    [
        ("#channel key", "#channel", "key"),
        ("channel key", "#channel", "key"),
        ("#channel", "#channel", None),
        ("channel", "#channel", None),
    ],
)
async def test_join(input_text, chan, key, event_loop):
    conn = MagicMock()
    conn.config = {}
    conn.bot = None

    event = CommandEvent(
        text=input_text,
        cmd_prefix=".",
        triggered_command="join",
        hook=MagicMock(),
        bot=conn.bot,
        conn=conn,
        channel="#foo",
        nick="foobaruser",
    )

    await async_util.run_func_with_args(event_loop, admin_bot.join, event)

    event.conn.join.assert_called_with(chan, key)


@pytest.mark.asyncio
async def test_me():
    event = MagicMock()
    event.chan = "#foo"
    event.nick = "bar"
    event.text = "do thing"

    def f(self, attr):
        return getattr(self, attr)

    event.__getitem__ = f
    event.event = event

    res = await func_utils.call_with_args(admin_bot.me, event)
    assert res is None
    assert event.mock_calls == [
        call.admin_log('bar used ME to make me ACT "do thing" in #foo.'),
        call.conn.ctcp("#foo", "ACTION", "do thing"),
    ]
