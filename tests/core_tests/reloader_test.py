from pathlib import Path
from unittest.mock import call, patch

import pytest

from cloudbot.reloader import ConfigReloader, PluginReloader
from tests.util.async_mock import AsyncMock


class TestConfigReload:
    @pytest.mark.asyncio()
    async def test_reload(self, mock_bot_factory, tmp_path, event_loop) -> None:
        config_file = tmp_path / "config.json"
        config_file.touch()
        bot = mock_bot_factory(loop=event_loop)
        reloader = ConfigReloader(bot)
        bot.running = True
        with patch.object(
            bot, "reload_config", create=True, new_callable=AsyncMock
        ) as mocked:
            await bot.loop.run_in_executor(
                None, reloader.reload, str(config_file)
            )

            assert mocked.mock_calls == [call()]

    @pytest.mark.asyncio()
    async def test_reload_not_running(
        self, mock_bot_factory, tmp_path, event_loop
    ):
        config_file = tmp_path / "config.json"
        config_file.touch()
        bot = mock_bot_factory(loop=event_loop)
        reloader = ConfigReloader(bot)
        bot.running = False
        with patch.object(
            bot, "reload_config", create=True, new_callable=AsyncMock
        ) as mocked:
            await bot.loop.run_in_executor(
                None, reloader.reload, str(config_file)
            )

            assert mocked.mock_calls == []


class TestPluginReload:
    @pytest.mark.asyncio()
    async def test_reload(self, mock_bot_factory, tmp_path, event_loop):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_file = plugin_dir / "plugin.py"
        plugin_file.touch()
        bot = mock_bot_factory(loop=event_loop)
        reloader = PluginReloader(bot)
        with patch.object(
            reloader, "_reload", new_callable=AsyncMock
        ) as mocked:
            await bot.loop.run_in_executor(
                None, reloader.reload, str(plugin_file)
            )

            assert mocked.mock_calls == [call(Path(str(plugin_file)))]

    @pytest.mark.asyncio()
    async def test_reload_no_path(self, mock_bot_factory, tmp_path, event_loop):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_file = plugin_dir / "plugin.py"
        bot = mock_bot_factory(loop=event_loop)
        reloader = PluginReloader(bot)
        with patch.object(
            reloader, "_reload", new_callable=AsyncMock
        ) as mocked:
            await bot.loop.run_in_executor(
                None, reloader.reload, str(plugin_file)
            )

            assert mocked.mock_calls == []

    @pytest.mark.asyncio()
    async def test_unload(self, mock_bot_factory, tmp_path, event_loop):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_file = plugin_dir / "plugin.py"
        plugin_file.touch()
        bot = mock_bot_factory(loop=event_loop)
        reloader = PluginReloader(bot)
        with patch.object(
            reloader, "_unload", new_callable=AsyncMock
        ) as mocked:
            await bot.loop.run_in_executor(
                None, reloader.unload, str(plugin_file)
            )

            assert mocked.mock_calls == [call(Path(str(plugin_file)))]
