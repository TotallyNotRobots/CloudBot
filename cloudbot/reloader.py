import asyncio
from abc import ABC
from pathlib import Path

from watchdog.events import PatternMatchingEventHandler


class Reloader(ABC):
    def __init__(self, bot, handler, pattern, recursive=False):
        self.bot = bot
        self.recursive = recursive
        self.event_handler = handler(self, patterns=[pattern])
        self.watch = None

    def start(self, path="."):
        self.watch = self.observer.schedule(
            self.event_handler, path=path, recursive=self.recursive
        )

    def stop(self):
        if self.watch:
            self.observer.unschedule(self.watch)
            self.watch = None

    def reload(self, path):
        pass

    def unload(self, path):
        pass

    @property
    def observer(self):
        return self.bot.observer


class PluginReloader(Reloader):
    def __init__(self, bot):
        super().__init__(bot, PluginEventHandler, "[!_]*.py", recursive=True)
        self.reloading = set()

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

    async def _reload(self, path):
        if path in self.reloading:
            # we already have a coroutine reloading
            return
        self.reloading.add(path)
        # we don't want to reload more than once every 200 milliseconds, so wait that long to make sure there
        # are no other file changes in that time.
        await asyncio.sleep(0.2)
        self.reloading.remove(path)
        await self.bot.plugin_manager.load_plugin(path)

    async def _unload(self, path):
        await self.bot.plugin_manager.unload_plugin(path)


class ConfigReloader(Reloader):
    def __init__(self, bot):
        super().__init__(
            bot, ConfigEventHandler, "*{}".format(bot.config.filename)
        )

    def reload(self, path):
        if self.bot.running:
            self.bot.logger.info("Config changed, triggering reload.")
            asyncio.run_coroutine_threadsafe(
                self.bot.reload_config(), self.bot.loop
            ).result()


class ReloadHandler(PatternMatchingEventHandler):
    def __init__(self, loader, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loader = loader

    @property
    def bot(self):
        return self.loader.bot


class PluginEventHandler(ReloadHandler):
    def on_created(self, event):
        self.loader.reload(event.src_path)

    def on_deleted(self, event):
        self.loader.unload(event.src_path)

    def on_modified(self, event):
        self.loader.reload(event.src_path)

    def on_moved(self, event):
        self.loader.unload(event.src_path)
        # only load if it's moved to a .py file
        end = ".py" if isinstance(event.dest_path, str) else b".py"
        if event.dest_path.endswith(end):
            self.loader.reload(event.dest_path)


class ConfigEventHandler(ReloadHandler):
    def on_any_event(self, event):
        self.loader.reload(getattr(event, "dest_path", event.src_path))
