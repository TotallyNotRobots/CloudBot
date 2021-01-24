from pathlib import Path
from unittest.mock import call, patch

import pytest

from cloudbot.reloader import ConfigReloader, PluginReloader
from tests.util.mock_bot import MockBot


class TestConfigReload:
    @pytest.mark.asyncio()
    async def test_reload(self, tmp_path) -> None:
        config_file = tmp_path / "config.json"
        config_file.touch()
        bot = MockBot()
        reloader = ConfigReloader(bot)
        bot.running = True
        with patch.object(bot, "reload_config", create=True) as mocked:
            future = bot.loop.create_future()
            future.set_result(True)

            async def coro():
                await future

            mocked.return_value = coro()

            await bot.loop.run_in_executor(
                None, reloader.reload, str(config_file)
            )

            assert mocked.mock_calls == [call()]

    @pytest.mark.asyncio()
    async def test_reload_not_running(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.touch()
        bot = MockBot()
        reloader = ConfigReloader(bot)
        bot.running = False
        with patch.object(bot, "reload_config", create=True) as mocked:
            future = bot.loop.create_future()
            future.set_result(True)

            async def coro():  # pragma: no cover
                await future

            mocked.return_value = coro()

            await bot.loop.run_in_executor(
                None, reloader.reload, str(config_file)
            )

            assert mocked.mock_calls == []


class TestPluginReload:
    @pytest.mark.asyncio()
    async def test_reload(self, tmp_path):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_file = plugin_dir / "plugin.py"
        plugin_file.touch()
        bot = MockBot()
        reloader = PluginReloader(bot)
        with patch.object(reloader, "_reload") as mocked:
            future = bot.loop.create_future()
            future.set_result(True)

            async def coro():
                await future

            mocked.return_value = coro()

            await bot.loop.run_in_executor(
                None, reloader.reload, str(plugin_file)
            )

            assert mocked.mock_calls == [call(Path(str(plugin_file)))]

    @pytest.mark.asyncio()
    async def test_reload_no_path(self, tmp_path):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_file = plugin_dir / "plugin.py"
        bot = MockBot()
        reloader = PluginReloader(bot)
        with patch.object(reloader, "_reload") as mocked:
            future = bot.loop.create_future()
            future.set_result(True)

            async def coro():  # pragma: no cover
                await future

            mocked.return_value = coro()

            await bot.loop.run_in_executor(
                None, reloader.reload, str(plugin_file)
            )

            assert mocked.mock_calls == []

    @pytest.mark.asyncio()
    async def test_unload(self, tmp_path):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_file = plugin_dir / "plugin.py"
        plugin_file.touch()
        bot = MockBot()
        reloader = PluginReloader(bot)
        with patch.object(reloader, "_unload") as mocked:
            future = bot.loop.create_future()
            future.set_result(True)

            async def coro():
                await future

            mocked.return_value = coro()

            await bot.loop.run_in_executor(
                None, reloader.unload, str(plugin_file)
            )

            assert mocked.mock_calls == [call(Path(str(plugin_file)))]
