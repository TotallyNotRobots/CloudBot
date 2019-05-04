from pathlib import Path

import pytest
from mock import MagicMock

from cloudbot.plugin import PluginManager


@pytest.fixture()
def mock_bot():
    yield MagicMock()


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
    mock_manager.bot.config = {}

    assert mock_manager.can_load('plugins.foo')

    mock_manager.bot.config = {
        'plugin_loading': {
            'use_whitelist': True,
            'whitelist': [
                'plugins.bar',
            ]
        }
    }
    assert not mock_manager.can_load('plugins.foo')

    mock_manager.bot.config = {
        'plugin_loading': {
            'use_whitelist': True,
            'whitelist': [
                'plugins.foo',
            ]
        }
    }
    assert mock_manager.can_load('plugins.foo')

    mock_manager.bot.config = {
        'plugin_loading': {
            'use_whitelist': False,
            'whitelist': [
                'plugins.bar',
            ],
            'blacklist': [
                'plugins.foo',
            ]
        }
    }
    assert not mock_manager.can_load('plugins.foo')

    mock_manager.bot.config = {
        'plugin_loading': {
            'use_whitelist': False,
            'whitelist': [
                'plugins.bar',
            ],
            'blacklist': [
            ]
        }
    }
    assert mock_manager.can_load('plugins.foo')
