import asyncio
import importlib

import pytest
from unittest.mock import MagicMock

from cloudbot.event import CommandEvent, Event
from cloudbot.util.func_utils import call_with_args
from plugins.attacks import ATTACKS, RespType
from plugins.foods import BASIC_FOOD


def _call(func, event):
    if asyncio.iscoroutinefunction(func):
        return event.loop.run_until_complete(call_with_args(func, event))

    return call_with_args(func, event)


def _do_test(plugin_name, loader, data_name, cmd, text='test _ data',
             is_nick_valid=None, nick=None, bot_nick=None):
    plugin = importlib.import_module('plugins.' + plugin_name)
    bot = MagicMock()
    bot.data_dir = 'data'
    bot.loop = asyncio.get_event_loop()
    event = Event(
        hook=MagicMock(), bot=bot,
        conn=MagicMock(), channel='#foo',
        nick=nick or 'foobar'
    )
    if bot_nick:
        event.conn.nick = bot_nick
    else:
        event.conn.nick = 'TestBot'

    if is_nick_valid:
        event.is_nick_valid = is_nick_valid

    if loader:
        _call(getattr(plugin, loader), event)

    if data_name:
        assert getattr(plugin, data_name)

    cmd_func = getattr(plugin, cmd)
    cmd_event = CommandEvent(
        text=text or '', cmd_prefix='.', hook=MagicMock(),
        triggered_command='foo', base_event=event
    )
    if is_nick_valid:
        cmd_event.is_nick_valid = is_nick_valid

    return _call(cmd_func, cmd_event), cmd_event


@pytest.mark.parametrize('plugin_name,loader,data_name,cmd', [
    ('fmk', 'load_fmk', 'fmklist', 'fmk'),
    ('kenm', 'load_kenm', 'kenm_data', 'kenm'),
    ('topicchange', 'load_topicchange', 'topicchange_data', 'topicchange'),
    ('cheer', 'load_cheers', 'cheers', 'cheer'),
    ('lenny', 'load_faces', 'lenny_data', 'lenny'),
    ('lenny', 'load_faces', 'lenny_data', 'flenny'),
    ('penis', None, None, 'penis'),
    ('reactions', 'load_macros', 'reaction_macros', 'deal_with_it'),
    ('reactions', 'load_macros', 'reaction_macros', 'face_palm'),
    ('reactions', 'load_macros', 'reaction_macros', 'head_desk'),
    ('reactions', 'load_macros', 'reaction_macros', 'my_fetish'),
])
def test_message_reply(plugin_name, loader, data_name, cmd):
    _, event = _do_test(plugin_name, loader, data_name, cmd, None)
    event.conn.message.assert_called()
    _, event = _do_test(plugin_name, loader, data_name, cmd)
    event.conn.message.assert_called()


@pytest.mark.parametrize('plugin_name,loader,data_name,cmd', [
    ('eightball', 'load_responses', 'responses', 'eightball'),
    ('drinks', 'load_drinks', 'drink_data', 'drink_cmd'),
    ('foods', 'load_foods', 'basic_food_data', 'potato'),
])
def test_action_reply(plugin_name, loader, data_name, cmd):
    _, event = _do_test(plugin_name, loader, data_name, cmd)
    event.conn.action.assert_called()


@pytest.mark.parametrize('plugin_name,loader,data_name,cmd', [
    ('verysmart', 'load_quotes', 'vsquotes', 'verysmart'),
    ('fortune', 'load_fortunes', 'fortunes', 'fortune'),
    ('gnomeagainsthumanity', 'shuffle_deck', 'gnomecards', 'CAHwhitecard'),
    ('gnomeagainsthumanity', 'shuffle_deck', 'gnomecards', 'CAHblackcard'),
])
def test_text_return(plugin_name, loader, data_name, cmd):
    res, _ = _do_test(plugin_name, loader, data_name, cmd)
    assert res


@pytest.mark.parametrize('food', [
    food.name for food in BASIC_FOOD
])
def test_foods(food):
    _, event = _do_test(
        'foods', 'load_foods', 'basic_food_data', food
    )
    event.conn.action.assert_called()
    _, event = _do_test(
        'foods', 'load_foods', 'basic_food_data', food, None
    )
    event.conn.action.assert_called()
    res, event = _do_test(
        'foods', 'load_foods', 'basic_food_data', food,
        is_nick_valid=lambda *args: False
    )
    assert res
    event.conn.action.assert_not_called()


@pytest.mark.parametrize('attack', [
    attack for attack in ATTACKS
])
def test_attacks(attack):
    _, event = _do_test(
        'attacks', 'load_attacks', 'attack_data', attack.name
    )

    if attack.response == RespType.ACTION:
        event.conn.action.assert_called()
    else:
        event.conn.message.assert_called()

    _, event = _do_test(
        'attacks', 'load_attacks', 'attack_data', attack.name
    )

    if attack.response == RespType.ACTION:
        event.conn.action.assert_called()
    else:
        event.conn.message.assert_called()

    _, event = _do_test(
        'attacks', 'load_attacks', 'attack_data', attack.name, 'yourself',
        bot_nick='foobot'
    )

    if attack.response is RespType.ACTION:
        event.conn.action.assert_called()
    else:
        event.conn.message.assert_called()

    if not attack.require_target:
        _, event = _do_test(
            'attacks', 'load_attacks', 'attack_data', attack.name, None
        )

        if attack.response is RespType.ACTION:  # pragma: no cover
            event.conn.action.assert_called()
        else:
            event.conn.message.assert_called()

    res, event = _do_test(
        'attacks', 'load_attacks', 'attack_data', attack.name,
        is_nick_valid=lambda *args: False
    )
    assert res
    event.conn.action.assert_not_called()
    event.conn.message.assert_not_called()
