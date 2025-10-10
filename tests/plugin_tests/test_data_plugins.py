import asyncio
import importlib
import random
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cloudbot.event import CommandEvent, Event
from cloudbot.util import async_util
from plugins import attacks, foods


async def _call(func, event):
    return await async_util.run_func_with_args(
        asyncio.get_running_loop(), func, event
    )


async def _do_test(
    plugin_name,
    loader,
    data_name,
    cmd,
    loop,
    mock_bot_factory,
    text: str | None = "test _ data",
    is_nick_valid=None,
    nick=None,
    bot_nick=None,
):
    plugin = importlib.import_module("plugins." + plugin_name)
    bot = mock_bot_factory(base_dir=Path().resolve(), loop=loop)
    event = Event(
        hook=MagicMock(),
        bot=bot,
        conn=MagicMock(),
        channel="#foo",
        nick=nick or "foobar",
    )

    if bot_nick:
        event.conn.nick = bot_nick
    else:
        event.conn.nick = "TestBot"

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
        with patch.object(cmd_event, "is_nick_valid", new=is_nick_valid):
            res = await _call(cmd_func, cmd_event), cmd_event
    else:
        res = await _call(cmd_func, cmd_event), cmd_event

    return res


@pytest.mark.asyncio
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
async def test_message_reply(
    plugin_name, loader, data_name, cmd, mock_bot_factory
):
    _, event = await _do_test(
        plugin_name,
        loader,
        data_name,
        cmd,
        asyncio.get_running_loop(),
        mock_bot_factory,
        None,
    )
    assert event.conn.message.called
    _, event = await _do_test(
        plugin_name,
        loader,
        data_name,
        cmd,
        asyncio.get_running_loop(),
        mock_bot_factory,
    )
    assert event.conn.message.called


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "plugin_name,loader,data_name,cmd",
    [
        ("eightball", "load_responses", "responses", "eightball"),
        ("foods", "load_foods", "basic_food_data", "potato"),
    ],
)
async def test_action_reply(
    plugin_name, loader, data_name, cmd, mock_bot_factory
):
    _, event = await _do_test(
        plugin_name,
        loader,
        data_name,
        cmd,
        asyncio.get_running_loop(),
        mock_bot_factory,
    )
    assert event.conn.action.called


@pytest.mark.asyncio
@pytest.mark.parametrize("seed", list(range(0, 100, 5)))
async def test_drinks(seed, mock_bot_factory):
    random.seed(seed)
    _, event = await _do_test(
        "drinks",
        "load_drinks",
        "drink_data",
        "drink_cmd",
        asyncio.get_running_loop(),
        mock_bot_factory,
    )
    assert event.conn.action.called


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "plugin_name,loader,data_name,cmd",
    [
        ("verysmart", "load_quotes", "vsquotes", "verysmart"),
        ("fortune", "load_fortunes", "fortunes", "fortune"),
        ("gnomeagainsthumanity", "shuffle_deck", "gnomecards", "CAHwhitecard"),
        ("gnomeagainsthumanity", "shuffle_deck", "gnomecards", "CAHblackcard"),
    ],
)
async def test_text_return(
    plugin_name, loader, data_name, cmd, mock_bot_factory
):
    res, _ = await _do_test(
        plugin_name,
        loader,
        data_name,
        cmd,
        asyncio.get_running_loop(),
        mock_bot_factory,
    )
    assert res


@pytest.mark.asyncio
@pytest.mark.parametrize("food", [food.name for food in foods.BASIC_FOOD])
async def test_foods(food, mock_bot_factory):
    _, event = await _do_test(
        "foods",
        "load_foods",
        "basic_food_data",
        food,
        asyncio.get_running_loop(),
        mock_bot_factory,
    )
    assert event.conn.action.called
    _, event = await _do_test(
        "foods",
        "load_foods",
        "basic_food_data",
        food,
        asyncio.get_running_loop(),
        mock_bot_factory,
        None,
    )
    assert event.conn.action.called
    res, event = await _do_test(
        "foods",
        "load_foods",
        "basic_food_data",
        food,
        asyncio.get_running_loop(),
        mock_bot_factory,
        is_nick_valid=lambda *args: False,
    )
    assert res
    event.conn.action.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("attack", [attack for attack in attacks.ATTACKS])
async def test_attacks(attack, mock_bot_factory):
    _, event = await _do_test(
        "attacks",
        "load_attacks",
        "attack_data",
        attack.name,
        asyncio.get_running_loop(),
        mock_bot_factory,
    )

    if attack.response == attacks.RespType.ACTION:
        assert event.conn.action.called
    else:
        assert event.conn.message.called

    _, event = await _do_test(
        "attacks",
        "load_attacks",
        "attack_data",
        attack.name,
        asyncio.get_running_loop(),
        mock_bot_factory,
    )

    if attack.response == attacks.RespType.ACTION:
        assert event.conn.action.called
    else:
        assert event.conn.message.called

    _, event = await _do_test(
        "attacks",
        "load_attacks",
        "attack_data",
        attack.name,
        asyncio.get_running_loop(),
        mock_bot_factory,
        "yourself",
        bot_nick="foobot",
    )

    if attack.response is attacks.RespType.ACTION:
        assert event.conn.action.called
    else:
        assert event.conn.message.called

    if not attack.require_target:
        _, event = await _do_test(
            "attacks",
            "load_attacks",
            "attack_data",
            attack.name,
            asyncio.get_running_loop(),
            mock_bot_factory,
            None,
        )

        if attack.response is attacks.RespType.ACTION:  # pragma: no cover
            assert event.conn.action.called
        else:
            assert event.conn.message.called

    res, event = await _do_test(
        "attacks",
        "load_attacks",
        "attack_data",
        attack.name,
        asyncio.get_running_loop(),
        mock_bot_factory,
        is_nick_valid=lambda *args: False,
    )
    assert res
    event.conn.action.assert_not_called()
    event.conn.message.assert_not_called()
