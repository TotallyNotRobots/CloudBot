import asyncio
import itertools
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cloudbot import hook
from cloudbot.plugin import PluginManager
from tests.util.mock_module import MockModule


@pytest.fixture()
def mock_bot():
    class MockBot:
        __slots__ = ('plugin_manager',)

        config = {}
        base_dir = Path().resolve()

        @property
        def loop(self):
            return asyncio.get_event_loop()

    yield MockBot()


@pytest.fixture()
def mock_manager(mock_bot):
    mock_bot.plugin_manager = mgr = PluginManager(mock_bot)
    yield mgr


def test_get_plugin(mock_manager):
    assert mock_manager.get_plugin('plugins/test.py') is None
    assert mock_manager.find_plugin('test') is None

    from cloudbot.plugin import Plugin

    file_path = Path('plugins').resolve() / 'test.py'
    file_name = file_path.name

    obj = Plugin(
        str(file_path),
        file_name,
        'test',
        MockModule(),
    )

    mock_manager._add_plugin(obj)

    assert mock_manager.get_plugin('plugins/test.py') is obj
    assert mock_manager.find_plugin('test') is obj

    mock_manager._rem_plugin(obj)

    assert mock_manager.get_plugin('plugins/test.py') is None
    assert mock_manager.find_plugin('test') is None


def test_can_load(mock_manager):
    mock_manager.bot.config.clear()

    assert mock_manager.can_load('plugins.foo')

    mock_manager.bot.config.update({
        'plugin_loading': {
            'use_whitelist': True,
            'whitelist': [
                'plugins.bar',
            ]
        }
    })
    assert not mock_manager.can_load('plugins.foo')

    mock_manager.bot.config.update({
        'plugin_loading': {
            'use_whitelist': True,
            'whitelist': [
                'plugins.foo',
            ]
        }
    })
    assert mock_manager.can_load('plugins.foo')

    mock_manager.bot.config.update({
        'plugin_loading': {
            'use_whitelist': False,
            'whitelist': [
                'plugins.bar',
            ],
            'blacklist': [
                'plugins.foo',
            ]
        }
    })
    assert not mock_manager.can_load('plugins.foo')

    mock_manager.bot.config.update({
        'plugin_loading': {
            'use_whitelist': False,
            'whitelist': [
                'plugins.bar',
            ],
            'blacklist': [
            ]
        }
    })
    assert mock_manager.can_load('plugins.foo')


@pytest.fixture()
def patch_import_module():
    with patch('importlib.import_module') as mocked:
        yield mocked


@pytest.fixture()
def patch_import_reload():
    with patch('importlib.reload') as mocked:
        yield mocked


def test_plugin_load(mock_manager, patch_import_module, patch_import_reload):
    patch_import_module.return_value = mod = MockModule()
    mock_manager.bot.loop.run_until_complete(
        mock_manager.load_plugin('plugins/test.py')
    )
    patch_import_module.assert_called_once_with('plugins.test')
    patch_import_reload.assert_not_called()
    assert mock_manager.get_plugin('plugins/test.py').code is mod

    patch_import_module.reset_mock()

    patch_import_reload.return_value = newmod = MockModule()

    mock_manager.bot.loop.run_until_complete(
        mock_manager.load_plugin('plugins/test.py')
    )

    patch_import_module.assert_called_once_with('plugins.test')
    patch_import_reload.assert_called_once_with(mod)

    assert mock_manager.get_plugin('plugins/test.py').code is newmod


class WeirdObject:
    """
    This represents an object that returns a value for any attribute you ask for
    """

    def __init__(self, func):
        self.func = func

    def __getattr__(self, item):
        return self.func(self, item)


def _test_weird_obj(patch_import_module, mock_manager, weird_obj):
    patch_import_module.return_value = MockModule(some_import=weird_obj)

    mock_manager.bot.loop.run_until_complete(
        mock_manager.load_plugin('plugins/test.py')
    )


def test_plugin_with_objs_none_attr(mock_manager, patch_import_module):
    _test_weird_obj(
        patch_import_module, mock_manager, WeirdObject(lambda *args: None)
    )


def test_plugin_with_objs_mock_attr(mock_manager, patch_import_module):
    _test_weird_obj(
        patch_import_module, mock_manager, WeirdObject(lambda *args: MagicMock())
    )


def test_plugin_with_objs_dict_attr(mock_manager, patch_import_module):
    _test_weird_obj(
        patch_import_module, mock_manager, WeirdObject(lambda *args: {})
    )


def test_plugin_with_objs_full_dict_attr(mock_manager, patch_import_module):
    _test_weird_obj(
        patch_import_module, mock_manager, WeirdObject(lambda *args: {
            'some_thing': object(),
        })
    )


def test_plugin_load_disabled(mock_manager, patch_import_module, patch_import_reload):
    patch_import_module.return_value = MockModule()
    mock_manager.bot.config.update({
        'plugin_loading': {
            'use_whitelist': True,
            'whitelist': [
                'plugins.bar',
            ]
        }
    })
    assert mock_manager.bot.loop.run_until_complete(
        mock_manager.load_plugin('plugins/test.py')
    ) is None

    patch_import_module.assert_not_called()
    patch_import_reload.assert_not_called()
    assert mock_manager.get_plugin('plugins/test.py') is None


def test_safe_resolve(mock_manager):
    base_path = Path("/some/path/that/doesn't/exist")
    path = mock_manager.safe_resolve(base_path)
    assert str(path) == str(base_path.absolute())
    assert path.is_absolute()
    assert not path.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize('do_sieve,sieve_allow,single_thread', list(
    itertools.product([True, False], [True, False], [True, False])
))
async def test_launch(
        mock_manager, patch_import_module, do_sieve,
        sieve_allow, single_thread
):
    called = False
    sieve_called = False

    @hook.command('test', do_sieve=do_sieve, singlethread=single_thread)
    def foo_cb():
        nonlocal called
        called = True

    @hook.sieve()
    def sieve_cb(_bot, _event, _hook):
        nonlocal sieve_called
        sieve_called = True
        if sieve_allow:
            return _event

        return None

    mod = MockModule()

    mod.sieve_cb = sieve_cb
    mod.foo_cb = foo_cb

    patch_import_module.return_value = mod

    await mock_manager.load_plugin('plugins/test.py')

    from cloudbot.event import CommandEvent

    event = CommandEvent(
        bot=mock_manager.bot,
        hook=mock_manager.commands['test'],
        cmd_prefix='.',
        text='',
        triggered_command='test',
    )

    result = await mock_manager.launch(event.hook, event)

    assert result == called and called == (sieve_allow or not do_sieve)
    assert sieve_called == do_sieve
