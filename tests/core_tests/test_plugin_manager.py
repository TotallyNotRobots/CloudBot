import asyncio
from pathlib import Path

import pytest
from mock import patch

from cloudbot.plugin import PluginManager


@pytest.fixture()
def mock_bot():
    class MockBot:
        __slots__ = ()

        loop = asyncio.get_event_loop()
        config = {}
        base_dir = Path().resolve()

    yield MockBot()


@pytest.fixture()
def mock_manager(mock_bot):
    yield PluginManager(mock_bot)


class MockModule:
    pass


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
    path = mock_manager.safe_resolve(Path("/some/path/that/doesn't/exist"))
    assert str(path) == "/some/path/that/doesn't/exist"
    assert path.is_absolute()
    assert not path.exists()
