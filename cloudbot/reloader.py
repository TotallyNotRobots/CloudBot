import asyncio
from abc import ABC
from pathlib import Path

from typing_extensions import override
from watchdog.events import PatternMatchingEventHandler


class Reloader(ABC):
    def __init__(self, bot, handler, pattern, recursive=False) -> None:
        self.bot = bot
        self.recursive = recursive
        self.event_handler = handler(self, patterns=[pattern])
        self.watch = None

    def start(self, path=".") -> None:
        self.watch = self.observer.schedule(
            self.event_handler, path=path, recursive=self.recursive
        )

    def stop(self) -> None:
        if self.watch:
            self.observer.unschedule(self.watch)
            self.watch = None

    def reload(self, path) -> None:
        pass

    def unload(self, path) -> None:
        pass

    @property
    def observer(self):
        return self.bot.observer


class PluginReloader(Reloader):
    def __init__(self, bot) -> None:
        super().__init__(bot, PluginEventHandler, "**/[!_]*.py", recursive=True)
        self.reloading = set[Path]()

    def reload(self, path: str) -> None:
        """
        Loads or reloads a module, given its file path. Thread safe.
        """
        path_obj = Path(path).resolve()
        if path_obj.exists():
            asyncio.run_coroutine_threadsafe(
                self._reload(path_obj), self.bot.loop
            ).result()

    def unload(self, path: str) -> None:
        """
        Unloads a module, given its file path. Thread safe.
        """
        path_obj = Path(path).resolve()
        asyncio.run_coroutine_threadsafe(
            self._unload(path_obj), self.bot.loop
        ).result()

    async def _reload(self, path: Path) -> None:
        if path in self.reloading:
            # we already have a coroutine reloading
            return
        self.reloading.add(path)
        # we don't want to reload more than once every 200 milliseconds, so wait that long to make sure there
        # are no other file changes in that time.
        await asyncio.sleep(0.2)
        self.reloading.remove(path)
        await self.bot.plugin_manager.load_plugin(path)

    async def _unload(self, path: Path) -> None:
        await self.bot.plugin_manager.unload_plugin(path)


class ConfigReloader(Reloader):
    def __init__(self, bot) -> None:
        super().__init__(bot, ConfigEventHandler, f"*{bot.config.filename}")

    @override
    def reload(self, path) -> None:
        if self.bot.running:
            self.bot.logger.info("Config changed, triggering reload.")
            asyncio.run_coroutine_threadsafe(
                self.bot.reload_config(), self.bot.loop
            ).result()


class ReloadHandler(PatternMatchingEventHandler):
    def __init__(self, loader, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.loader = loader

    @property
    def bot(self):
        return self.loader.bot


class PluginEventHandler(ReloadHandler):
    def on_created(self, event) -> None:
        self.loader.reload(event.src_path)

    def on_deleted(self, event) -> None:
        self.loader.unload(event.src_path)

    def on_modified(self, event) -> None:
        self.loader.reload(event.src_path)

    def on_moved(self, event) -> None:
        self.loader.unload(event.src_path)
        # only load if it's moved to a .py file
        end = ".py" if isinstance(event.dest_path, str) else b".py"
        if event.dest_path.endswith(end):
            self.loader.reload(event.dest_path)


class ConfigEventHandler(ReloadHandler):
    def on_created(self, event) -> None:
        self.loader.reload(event.src_path)

    def on_deleted(self, event) -> None:
        self.loader.reload(event.src_path)

    def on_modified(self, event) -> None:
        self.loader.reload(event.src_path)

    def on_moved(self, event) -> None:
        self.loader.reload(event.dest_path)
