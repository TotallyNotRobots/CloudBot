import asyncio
import importlib

import pytest
from mock import MagicMock

from cloudbot.event import CommandEvent, Event
from cloudbot.util.func_utils import call_with_args


def _call(func, event):
    if asyncio.iscoroutinefunction(func):
        return event.loop.run_until_complete(call_with_args(func, event))

    return call_with_args(func, event)


def _do_test(plugin_name, loader, data_name, cmd, text='test _ data'):
    plugin = importlib.import_module('plugins.' + plugin_name)
    bot = MagicMock()
    bot.data_dir = 'data'
    bot.loop = asyncio.get_event_loop()
    event = Event(
        hook=MagicMock(), bot=bot,
        conn=MagicMock(), channel='#foo'
    )
    if loader:
        _call(getattr(plugin, loader), event)
    if data_name:
        assert getattr(plugin, data_name)

    cmd_func = getattr(plugin, cmd)
    cmd_event = CommandEvent(
        text=text or '', cmd_prefix='.', hook=MagicMock(),
        triggered_command='foo', base_event=event
    )

    return _call(cmd_func, cmd_event), cmd_event


@pytest.mark.parametrize('plugin_name,loader,data_name,cmd', [
    ('fmk', 'load_fmk', 'fmklist', 'fmk'),
    ('kenm', 'load_kenm', 'kenm_data', 'kenm'),
    ('topicchange', 'load_topicchange', 'topicchange_data', 'topicchange'),
    ('cheer', 'load_cheers', 'cheers', 'cheer'),
    ('lenny', 'load_faces', 'lenny_data', 'lenny'),
    ('lenny', 'load_faces', 'lenny_data', 'flenny'),
    ('penis', None, None, 'penis'),
])
def test_message_reply(plugin_name, loader, data_name, cmd):
    _, event = _do_test(plugin_name, loader, data_name, cmd, None)
    event.conn.message.assert_called()
    _, event = _do_test(plugin_name, loader, data_name, cmd)
    event.conn.message.assert_called()


@pytest.mark.parametrize('plugin_name,loader,data_name,cmd', [
    ('eightball', 'load_responses', 'responses', 'eightball'),
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
