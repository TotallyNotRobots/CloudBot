import asyncio
import importlib
import random
from typing import Optional
from unittest.mock import MagicMock

import pytest

from cloudbot.event import CommandEvent, Event
from cloudbot.util.func_utils import call_with_args
from plugins.attacks import ATTACKS, RespType
from plugins.foods import BASIC_FOOD
from tests.util import test_data_dir


async def _call(func, event):
    if asyncio.iscoroutinefunction(func):
        return await call_with_args(func, event)

    return call_with_args(func, event)


async def _do_test(
    plugin_name,
    loader,
    data_name,
    cmd,
    text: Optional[str] = "test _ data",
    is_nick_valid=None,
    nick=None,
    bot_nick=None,
):
    plugin = importlib.import_module("plugins." + plugin_name)
    bot = MagicMock()
    bot.data_dir = str(test_data_dir / ".." / ".." / "data")
    bot.loop = asyncio.get_event_loop()
    conn = MagicMock()
    conn.loop = bot.loop
    event = Event(
        hook=MagicMock(),
        bot=bot,
        conn=conn,
        channel="#foo",
        nick=nick or "foobar",
    )

    if bot_nick:
        event.conn.nick = bot_nick
    else:
        event.conn.nick = "TestBot"

    if is_nick_valid:
        event.is_nick_valid = is_nick_valid

    if loader:
        await _call(getattr(plugin, loader), event)

    if data_name:
        assert getattr(plugin, data_name)

    cmd_func = getattr(plugin, cmd)
    cmd_event = CommandEvent(
        text=text or "",
        cmd_prefix=".",
        hook=MagicMock(),
        triggered_command="foo",
        base_event=event,
    )
    if is_nick_valid:
        cmd_event.is_nick_valid = is_nick_valid

    return (await _call(cmd_func, cmd_event)), cmd_event


@pytest.mark.parametrize(
    "plugin_name,loader,data_name,cmd",
    [
        ("fmk", "load_fmk", "fmklist", "fmk"),
        ("kenm", "load_kenm", "kenm_data", "kenm"),
        ("topicchange", "load_topicchange", "topicchange_data", "topicchange"),
        ("cheer", "load_cheers", "cheers", "cheer"),
        ("lenny", "load_faces", "lenny_data", "lenny"),
        ("lenny", "load_faces", "lenny_data", "flenny"),
        ("penis", None, None, "penis"),
        ("reactions", "load_macros", "reaction_macros", "deal_with_it"),
        ("reactions", "load_macros", "reaction_macros", "face_palm"),
        ("reactions", "load_macros", "reaction_macros", "head_desk"),
        ("reactions", "load_macros", "reaction_macros", "my_fetish"),
    ],
)
@pytest.mark.asyncio()
async def test_message_reply(plugin_name, loader, data_name, cmd):
    _, event = await _do_test(plugin_name, loader, data_name, cmd, None)
    assert event.conn.message.called
    _, event = await _do_test(plugin_name, loader, data_name, cmd)
    assert event.conn.message.called


@pytest.mark.parametrize(
    "plugin_name,loader,data_name,cmd",
    [
        ("eightball", "load_responses", "responses", "eightball"),
        ("foods", "load_foods", "basic_food_data", "potato"),
    ],
)
@pytest.mark.asyncio()
async def test_action_reply(plugin_name, loader, data_name, cmd):
    _, event = await _do_test(plugin_name, loader, data_name, cmd)
    assert event.conn.action.called


@pytest.mark.parametrize("seed", list(range(0, 100, 5)))
@pytest.mark.asyncio()
async def test_drinks(seed):
    random.seed(seed)
    _, event = await _do_test(
        "drinks", "load_drinks", "drink_data", "drink_cmd"
    )
    assert event.conn.action.called


@pytest.mark.parametrize(
    "plugin_name,loader,data_name,cmd",
    [
        ("verysmart", "load_quotes", "vsquotes", "verysmart"),
        ("fortune", "load_fortunes", "fortunes", "fortune"),
        ("gnomeagainsthumanity", "shuffle_deck", "gnomecards", "CAHwhitecard"),
        ("gnomeagainsthumanity", "shuffle_deck", "gnomecards", "CAHblackcard"),
    ],
)
@pytest.mark.asyncio()
async def test_text_return(plugin_name, loader, data_name, cmd):
    res, _ = await _do_test(plugin_name, loader, data_name, cmd)
    assert res


@pytest.mark.parametrize("food", [food.name for food in BASIC_FOOD])
@pytest.mark.asyncio()
async def test_foods(food):
    _, event = await _do_test("foods", "load_foods", "basic_food_data", food)
    assert event.conn.action.called
    _, event = await _do_test(
        "foods", "load_foods", "basic_food_data", food, None
    )
    assert event.conn.action.called
    res, event = await _do_test(
        "foods",
        "load_foods",
        "basic_food_data",
        food,
        is_nick_valid=lambda *args: False,
    )
    assert res
    event.conn.action.assert_not_called()


@pytest.mark.parametrize("attack", [attack for attack in ATTACKS])
@pytest.mark.asyncio()
async def test_attacks(attack):
    _, event = await _do_test(
        "attacks", "load_attacks", "attack_data", attack.name
    )

    if attack.response == RespType.ACTION:
        assert event.conn.action.called
    else:
        assert event.conn.message.called

    _, event = await _do_test(
        "attacks", "load_attacks", "attack_data", attack.name
    )

    if attack.response == RespType.ACTION:
        assert event.conn.action.called
    else:
        assert event.conn.message.called

    _, event = await _do_test(
        "attacks",
        "load_attacks",
        "attack_data",
        attack.name,
        "yourself",
        bot_nick="foobot",
    )

    if attack.response is RespType.ACTION:
        assert event.conn.action.called
    else:
        assert event.conn.message.called

    if not attack.require_target:
        _, event = await _do_test(
            "attacks", "load_attacks", "attack_data", attack.name, None
        )

        if attack.response is RespType.ACTION:  # pragma: no cover
            assert event.conn.action.called
        else:
            assert event.conn.message.called

    res, event = await _do_test(
        "attacks",
        "load_attacks",
        "attack_data",
        attack.name,
        is_nick_valid=lambda *args: False,
    )
    assert res
    event.conn.action.assert_not_called()
    event.conn.message.assert_not_called()
