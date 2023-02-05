import asyncio
import importlib
import logging
import sys
import typing
from collections import defaultdict
from functools import partial
from operator import attrgetter
from pathlib import Path
from typing import Dict, List, MutableMapping, Optional, Tuple, Type, cast
from weakref import WeakValueDictionary

import sqlalchemy
from sqlalchemy import Table

from cloudbot.event import Event, EventType, PostHookEvent
from cloudbot.plugin_hooks import (
    CapHook,
    CommandHook,
    ConfigHook,
    EventHook,
    RawHook,
    RegexHook,
    hook_name_to_plugin,
)
from cloudbot.util import HOOK_ATTR, LOADED_ATTR, async_util, database
from cloudbot.util.func_utils import call_with_args

logger = logging.getLogger("cloudbot")


def find_hooks(parent, module):
    hooks = defaultdict(list)
    for func in module.__dict__.values():
        if hasattr(func, HOOK_ATTR) and not hasattr(func, "_not_" + HOOK_ATTR):
            # if it has cloudbot hook
            func_hooks = getattr(func, HOOK_ATTR)

            for hook_type, func_hook in func_hooks.items():
                hooks[hook_type].append(
                    hook_name_to_plugin(hook_type)(parent, func_hook)
                )

            # delete the hook to free memory
            delattr(func, HOOK_ATTR)

    return hooks


def find_tables(code):
    tables = []
    for obj in code.__dict__.values():
        if (
            isinstance(obj, sqlalchemy.Table)
            and obj.metadata == database.metadata
        ):
            # if it's a Table, and it's using our metadata, append it to the list
            tables.append(obj)
        elif isinstance(obj, type) and issubclass(obj, database.Base):
            obj = cast(Type[database.Base], obj)
            tables.append(obj.__table__)

    return tables


class PluginManager:
    """
    PluginManager is the core of CloudBot plugin loading.

    PluginManager loads Plugins, and adds their Hooks to easy-access dicts/lists.

    Each Plugin represents a file, and loads hooks onto itself using find_hooks.

    Plugins are the lowest level of abstraction in this class. There are four different plugin types:
    - CommandPlugin is for bot commands
    - RawPlugin hooks onto irc_raw irc lines
    - RegexPlugin loads a regex parameter, and executes on irc lines which match the regex
    - SievePlugin is a catch-all sieve, which all other plugins go through before being executed.
    """

    def __init__(self, bot):
        """
        Creates a new PluginManager. You generally only need to do this from inside cloudbot.bot.CloudBot
        """
        self.bot = bot

        self.plugins: Dict[str, Plugin] = {}
        self._plugin_name_map: MutableMapping[
            str, Plugin
        ] = WeakValueDictionary()
        self.commands: Dict[str, CommandHook] = {}
        self.raw_triggers: Dict[str, List[RawHook]] = defaultdict(list)
        self.catch_all_triggers: List[RawHook] = []
        self.event_type_hooks: Dict[EventType, List[EventHook]] = defaultdict(
            list
        )
        self.regex_hooks: List[Tuple[typing.Pattern, RegexHook]] = []
        self.sieves = []
        self.cap_hooks: Dict[str, Dict[str, List[CapHook]]] = {
            "on_available": defaultdict(list),
            "on_ack": defaultdict(list),
        }
        self.connect_hooks = []
        self.out_sieves = []
        self.hook_hooks = defaultdict(list)
        self.perm_hooks = defaultdict(list)
        self.config_hooks: List[ConfigHook] = []

    def _add_plugin(self, plugin: "Plugin"):
        self.plugins[plugin.file_path] = plugin
        self._plugin_name_map[plugin.title] = plugin

    def _rem_plugin(self, plugin: "Plugin"):
        del self.plugins[plugin.file_path]
        del self._plugin_name_map[plugin.title]

    def find_plugin(self, title):
        """
        Finds a loaded plugin and returns its Plugin object
        :param title: the title of the plugin to find
        :return: The Plugin object if it exists, otherwise None
        """
        return self._plugin_name_map.get(title)

    def safe_resolve(self, path_obj: Path) -> Path:
        """Resolve the parts of a path that exist, allowing a non-existant path
        to be resolved to allow resolution of its parents

        :param path_obj: The `Path` object to resolve
        :return: The safely resolved `Path`
        """
        unresolved = []
        while not path_obj.exists():
            unresolved.append(path_obj.name)
            path_obj = path_obj.parent

        path_obj = path_obj.resolve()

        for part in reversed(unresolved):
            path_obj /= part

        return path_obj

    def get_plugin(self, path) -> Optional["Plugin"]:
        """
        Find a loaded plugin from its filename

        :param path: The plugin's filepath
        :return: A Plugin object or None
        """
        path_obj = Path(path)

        return self.plugins.get(str(self.safe_resolve(path_obj)))

    def can_load(self, plugin_title, noisy=True):
        pl = self.bot.config.get("plugin_loading")
        if not pl:
            return True

        if pl.get("use_whitelist", False):
            if plugin_title not in pl.get("whitelist", []):
                if noisy:
                    logger.info(
                        'Not loading plugin module "%s": '
                        "plugin not whitelisted",
                        plugin_title,
                    )

                return False

            return True

        if plugin_title in pl.get("blacklist", []):
            if noisy:
                logger.info(
                    'Not loading plugin module "%s": plugin blacklisted',
                    plugin_title,
                )

            return False

        return True

    async def load_all(self, plugin_dir):
        """
        Load a plugin from each *.py file in the given directory.

        Won't load any plugins listed in "disabled_plugins".
        """
        plugin_dir = Path(plugin_dir)
        # Load all .py files in the plugins directory and any subdirectory
        # But ignore files starting with _
        path_list = plugin_dir.rglob("[!_]*.py")
        # Load plugins asynchronously :O
        await asyncio.gather(*[self.load_plugin(path) for path in path_list])

    async def unload_all(self):
        await asyncio.gather(
            *[self.unload_plugin(path) for path in self.plugins],
        )

    def _load_mod(self, name):
        plugin_module = importlib.import_module(name)
        # if this plugin was loaded before, reload it
        if hasattr(plugin_module, LOADED_ATTR):
            plugin_module = importlib.reload(plugin_module)

        setattr(plugin_module, LOADED_ATTR, True)
        return plugin_module

    async def load_plugin(self, path):
        """
        Loads a plugin from the given path and plugin object,
        then registers all hooks from that plugin.
        """

        path = Path(path)
        file_path = self.safe_resolve(path)
        file_name = file_path.name
        # Resolve the path relative to the current directory
        plugin_path = file_path.relative_to(self.bot.base_dir)
        title = ".".join(plugin_path.parts[1:]).rsplit(".", 1)[0]

        if not self.can_load(title):
            return

        # make sure to unload the previously loaded plugin from this path, if it was loaded.
        if self.get_plugin(file_path):
            await self.unload_plugin(file_path)

        module_name = "plugins.{}".format(title)
        try:
            plugin_module = self._load_mod(module_name)
        except Exception:
            logger.exception("Error loading %s:", title)
            return

        # create the plugin
        plugin = Plugin(str(file_path), file_name, title, plugin_module)

        # proceed to register hooks

        # create database tables
        await plugin.create_tables(self.bot)

        # run on_start hooks
        for on_start_hook in plugin.hooks["on_start"]:
            success = await self.launch(
                on_start_hook, Event(bot=self.bot, hook=on_start_hook)
            )
            if not success:
                logger.warning(
                    "Not registering hooks from plugin %s: on_start hook errored",
                    plugin.title,
                )

                # unregister databases
                plugin.unregister_tables(self.bot)
                return

        self._add_plugin(plugin)

        for on_cap_available_hook in plugin.hooks["on_cap_available"]:
            for cap in on_cap_available_hook.caps:
                self.cap_hooks["on_available"][cap.casefold()].append(
                    on_cap_available_hook
                )
            self._log_hook(on_cap_available_hook)

        for on_cap_ack_hook in plugin.hooks["on_cap_ack"]:
            for cap in on_cap_ack_hook.caps:
                self.cap_hooks["on_ack"][cap.casefold()].append(on_cap_ack_hook)
            self._log_hook(on_cap_ack_hook)

        for periodic_hook in plugin.hooks["periodic"]:
            task = async_util.wrap_future(self._start_periodic(periodic_hook))
            plugin.tasks.append(task)
            self._log_hook(periodic_hook)

        # register commands
        for command_hook in plugin.hooks["command"]:
            for alias in command_hook.aliases:
                if alias in self.commands:
                    logger.warning(
                        "Plugin %s attempted to register command %s which was "
                        "already registered by %s. Ignoring new assignment.",
                        plugin.title,
                        alias,
                        self.commands[alias].plugin.title,
                    )
                else:
                    self.commands[alias] = command_hook
            self._log_hook(command_hook)

        # register raw hooks
        for raw_hook in plugin.hooks["irc_raw"]:
            if raw_hook.is_catch_all():
                self.catch_all_triggers.append(raw_hook)
            else:
                for trigger in raw_hook.triggers:
                    if trigger in self.raw_triggers:
                        self.raw_triggers[trigger].append(raw_hook)
                    else:
                        self.raw_triggers[trigger] = [raw_hook]
            self._log_hook(raw_hook)

        # register events
        for event_hook in plugin.hooks["event"]:
            for event_type in event_hook.types:
                if event_type in self.event_type_hooks:
                    self.event_type_hooks[event_type].append(event_hook)
                else:
                    self.event_type_hooks[event_type] = [event_hook]
            self._log_hook(event_hook)

        # register regexps
        for regex_hook in plugin.hooks["regex"]:
            for regex_match in regex_hook.regexes:
                self.regex_hooks.append((regex_match, regex_hook))
            self._log_hook(regex_hook)

        # register sieves
        for sieve_hook in plugin.hooks["sieve"]:
            self.sieves.append(sieve_hook)
            self._log_hook(sieve_hook)

        # register connect hooks
        for connect_hook in plugin.hooks["on_connect"]:
            self.connect_hooks.append(connect_hook)
            self._log_hook(connect_hook)

        for out_hook in plugin.hooks["irc_out"]:
            self.out_sieves.append(out_hook)
            self._log_hook(out_hook)

        for post_hook in plugin.hooks["post_hook"]:
            self.hook_hooks["post"].append(post_hook)
            self._log_hook(post_hook)

        for config_hook in plugin.hooks["config"]:
            self.config_hooks.append(config_hook)
            self._log_hook(config_hook)

        for perm_hook in plugin.hooks["perm_check"]:
            for perm in perm_hook.perms:
                self.perm_hooks[perm].append(perm_hook)

            self._log_hook(perm_hook)

        # Sort hooks
        self._sort_hooks()

        # we don't need this anymore
        del plugin.hooks["on_start"]

    def _sort_hooks(self) -> None:
        def _sort_list(hooks):
            hooks.sort(key=attrgetter("priority"))

        def _sort_dict(hooks):
            for items in hooks.values():
                _sort_list(items)

        _sort_dict(self.raw_triggers)
        _sort_list(self.catch_all_triggers)
        _sort_dict(self.event_type_hooks)
        self.regex_hooks.sort(key=lambda x: x[1].priority)
        _sort_list(self.sieves)
        for d in self.cap_hooks.values():
            _sort_dict(d)

        _sort_list(self.connect_hooks)
        _sort_list(self.out_sieves)
        _sort_dict(self.hook_hooks)
        _sort_dict(self.perm_hooks)
        _sort_list(self.config_hooks)

    async def unload_plugin(self, path):
        """
        Unloads the plugin from the given path, unregistering all hooks from the plugin.

        Returns True if the plugin was unloaded, False if the plugin wasn't loaded in the first place.
        """
        path = Path(path)
        file_path = self.safe_resolve(path)

        # make sure this plugin is actually loaded
        plugin = self.get_plugin(file_path)
        if not plugin:
            return False

        for on_cap_available_hook in plugin.hooks["on_cap_available"]:
            available_hooks = self.cap_hooks["on_available"]
            for cap in on_cap_available_hook.caps:
                cap_cf = cap.casefold()
                available_hooks[cap_cf].remove(on_cap_available_hook)
                if not available_hooks[cap_cf]:
                    del available_hooks[cap_cf]

        for on_cap_ack in plugin.hooks["on_cap_ack"]:
            ack_hooks = self.cap_hooks["on_ack"]
            for cap in on_cap_ack.caps:
                cap_cf = cap.casefold()
                ack_hooks[cap_cf].remove(on_cap_ack)
                if not ack_hooks[cap_cf]:
                    del ack_hooks[cap_cf]

        # unregister commands
        for command_hook in plugin.hooks["command"]:
            for alias in command_hook.aliases:
                if (
                    alias in self.commands
                    and self.commands[alias] == command_hook
                ):
                    # we need to make sure that there wasn't a conflict, so we don't delete another plugin's command
                    del self.commands[alias]

        # unregister raw hooks
        for raw_hook in plugin.hooks["irc_raw"]:
            if raw_hook.is_catch_all():
                self.catch_all_triggers.remove(raw_hook)
            else:
                for trigger in raw_hook.triggers:
                    # this can't be not true
                    assert trigger in self.raw_triggers
                    self.raw_triggers[trigger].remove(raw_hook)
                    # if that was the last hook for this trigger
                    if not self.raw_triggers[trigger]:
                        del self.raw_triggers[trigger]

        # unregister events
        for event_hook in plugin.hooks["event"]:
            for event_type in event_hook.types:
                # this can't be not true
                assert event_type in self.event_type_hooks
                self.event_type_hooks[event_type].remove(event_hook)
                # if that was the last hook for this event type
                if not self.event_type_hooks[event_type]:
                    del self.event_type_hooks[event_type]

        # unregister regexps
        for regex_hook in plugin.hooks["regex"]:
            for regex_match in regex_hook.regexes:
                self.regex_hooks.remove((regex_match, regex_hook))

        # unregister sieves
        for sieve_hook in plugin.hooks["sieve"]:
            self.sieves.remove(sieve_hook)

        # unregister connect hooks
        for connect_hook in plugin.hooks["on_connect"]:
            self.connect_hooks.remove(connect_hook)

        for out_hook in plugin.hooks["irc_out"]:
            self.out_sieves.remove(out_hook)

        for post_hook in plugin.hooks["post_hook"]:
            self.hook_hooks["post"].remove(post_hook)

        for config_hook in plugin.hooks["config"]:
            self.config_hooks.remove(config_hook)

        for perm_hook in plugin.hooks["perm_check"]:
            for perm in perm_hook.perms:
                self.perm_hooks[perm].remove(perm_hook)

        # Run on_stop hooks
        for on_stop_hook in plugin.hooks["on_stop"]:
            event = Event(bot=self.bot, hook=on_stop_hook)
            await self.launch(on_stop_hook, event)

        # unregister databases
        plugin.unregister_tables(self.bot)

        task_count = len(plugin.tasks)
        if task_count > 0:
            logger.debug("Cancelling running tasks in %s", plugin.title)
            for task in plugin.tasks:
                task.cancel()

            logger.info("Cancelled %d tasks from %s", task_count, plugin.title)

        # remove last reference to plugin
        self._rem_plugin(plugin)

        if self.bot.config.get("logging", {}).get("show_plugin_loading", True):
            logger.info("Unloaded all plugins from %s", plugin.title)

        return True

    def _log_hook(self, hook):
        """
        Logs registering a given hook
        """
        if self.bot.config.get("logging", {}).get("show_plugin_loading", True):
            logger.info("Loaded %s", hook)
            logger.debug("Loaded %r", hook)

    def _execute_hook_threaded(self, hook, event):
        """ """
        event.prepare_threaded()

        try:
            return call_with_args(hook.function, event)
        finally:
            event.close_threaded()

    async def _execute_hook_sync(self, hook, event):
        """ """
        await event.prepare()

        try:
            return await call_with_args(hook.function, event)
        finally:
            await event.close()

    async def internal_launch(self, hook, event):
        """
        Launches a hook with the data from [event]
        :param hook: The hook to launch
        :param event: The event providing data for the hook
        :return: a tuple of (ok, result) where ok is a boolean that determines if the hook ran without error and result
            is the result from the hook
        """
        if hook.threaded:
            coro = self.bot.loop.run_in_executor(
                None, self._execute_hook_threaded, hook, event
            )
        else:
            coro = self._execute_hook_sync(hook, event)

        task = async_util.wrap_future(coro)
        hook.plugin.tasks.append(task)
        try:
            out = await task
            ok = True
        except Exception:
            logger.exception("Error in hook %s", hook.description)
            ok = False
            out = sys.exc_info()

        hook.plugin.tasks.remove(task)

        return ok, out

    async def _execute_hook(self, hook, event):
        """
        Runs the specific hook with the given bot and event.

        Returns False if the hook errored, True otherwise.
        """
        ok, out = await self.internal_launch(hook, event)
        result, error = None, None
        if ok is True:
            result = out
        else:
            error = out

        post_event = partial(
            PostHookEvent,
            launched_hook=hook,
            launched_event=event,
            bot=event.bot,
            conn=event.conn,
            result=result,
            error=error,
        )
        for post_hook in self.hook_hooks["post"]:
            success, res = await self.internal_launch(
                post_hook, post_event(hook=post_hook)
            )
            if success and res is False:
                break

        return ok

    async def _sieve(self, sieve, event, hook):
        """ """
        if sieve.threaded:
            coro = self.bot.loop.run_in_executor(
                None, sieve.function, self.bot, event, hook
            )
        else:
            coro = sieve.function(self.bot, event, hook)

        result, error = None, None
        task = async_util.wrap_future(coro)
        sieve.plugin.tasks.append(task)
        try:
            result = await task
        except Exception:
            logger.exception(
                "Error running sieve %s on %s:",
                sieve.description,
                hook.description,
            )
            error = sys.exc_info()

        sieve.plugin.tasks.remove(task)

        post_event = partial(
            PostHookEvent,
            launched_hook=sieve,
            launched_event=event,
            bot=event.bot,
            conn=event.conn,
            result=result,
            error=error,
        )
        for post_hook in self.hook_hooks["post"]:
            success, res = await self.internal_launch(
                post_hook, post_event(hook=post_hook)
            )
            if success and res is False:
                break

        return result

    async def _start_periodic(self, hook):
        interval = hook.interval
        initial_interval = hook.initial_interval
        await asyncio.sleep(initial_interval)

        while True:
            event = Event(bot=self.bot, hook=hook)
            await self.launch(hook, event)
            await asyncio.sleep(interval)

    async def _launch(self, hook, event):
        # we don't need sieves on on_start hooks.
        if hook.do_sieve and hook.type not in (
            "on_start",
            "on_stop",
            "periodic",
        ):
            for sieve in self.bot.plugin_manager.sieves:
                event = await self._sieve(sieve, event, hook)
                if event is None:
                    return False

        return await self._execute_hook(hook, event)

    async def launch(self, hook, event):
        """
        Dispatch a given event to a given hook using a given bot object.

        Returns False if the hook didn't run successfully, and True if it ran successfully.
        """

        if hook.lock:
            async with hook.lock:
                return await self._launch(hook, event)

        return await self._launch(hook, event)


def _create_table(table: Table, bot):
    table.create(bot.db_engine, checkfirst=True)


class Plugin:
    """
    Each Plugin represents a plugin file, and contains loaded hooks.
    """

    def __init__(self, filepath, filename, title, code):
        """ """
        self.tasks = []
        self.file_path = filepath
        self.file_name = filename
        self.title = title
        self.hooks = find_hooks(self, code)
        # we need to find tables for each plugin so that they can be unloaded from the global metadata when the
        # plugin is reloaded
        self.tables = find_tables(code)
        # Keep a reference to this in case another plugin needs to access it
        self.code = code

    async def create_tables(self, bot):
        """
        Creates all sqlalchemy Tables that are registered in this plugin
        """
        if self.tables:
            # if there are any tables

            logger.info("Registering tables for %s", self.title)

            for table in self.tables:
                await bot.loop.run_in_executor(None, _create_table, table, bot)

    def unregister_tables(self, bot):
        """
        Unregisters all sqlalchemy Tables registered to the global metadata by this plugin
        """
        if self.tables:
            # if there are any tables
            logger.info("Unregistering tables for %s", self.title)

            for table in self.tables:
                database.metadata.remove(table)
