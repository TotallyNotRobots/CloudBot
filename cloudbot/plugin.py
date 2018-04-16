import asyncio
import importlib
import inspect
import logging
import sys
import time
import warnings
from collections import defaultdict
from functools import partial
from itertools import chain
from operator import attrgetter
from pathlib import Path
from weakref import WeakValueDictionary

import sqlalchemy

from cloudbot.event import Event, PostHookEvent
from cloudbot.hook import get_hooks
from cloudbot.hooks.actions import Action
from cloudbot.hooks.basic import BaseHook
from cloudbot.hooks.priority import Priority
from cloudbot.hooks.types import HookTypes
from cloudbot.util import database, async_util
from cloudbot.util.async_util import run_func_with_args

logger = logging.getLogger("cloudbot")


def find_hooks(parent, module):
    """
    :type parent: Plugin
    :type module: object
    :rtype: dict
    """
    # set the loaded flag
    module._cloudbot_loaded = True
    hooks = defaultdict(list)
    for name, func in module.__dict__.items():
        try:
            func_hooks = get_hooks(func)
        except AttributeError:
            continue

        if not isinstance(func_hooks, dict):
            continue

        for hook_type, func_hook in func_hooks.items():  # type: str, BaseHook
            hooks[hook_type].append(func_hook.make_full_hook(parent))

    return hooks


def find_tables(code):
    """
    :type code: object
    :rtype: list[sqlalchemy.Table]
    """
    tables = []
    for name, obj in code.__dict__.items():
        if isinstance(obj, sqlalchemy.Table) and obj.metadata == database.metadata:
            # if it's a Table, and it's using our metadata, append it to the list
            tables.append(obj)

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

    :type bot: cloudbot.bot.CloudBot
    :type plugins: dict[str, Plugin]
    :type commands: dict[str, CommandHook]
    :type raw_triggers: dict[str, list[RawHook]]
    :type catch_all_triggers: list[RawHook]
    :type event_type_hooks: dict[cloudbot.event.EventType, list[EventHook]]
    :type regex_hooks: list[(re.__Regex, RegexHook)]
    :type sieves: list[SieveHook]
    """

    def __init__(self, bot):
        """
        Creates a new PluginManager. You generally only need to do this from inside cloudbot.bot.CloudBot
        :type bot: cloudbot.bot.CloudBot
        """
        self.bot = bot

        self.plugins = {}
        self._plugin_name_map = WeakValueDictionary()
        self.commands = {}
        self.raw_triggers = {}
        self.catch_all_triggers = []
        self.event_type_hooks = {}
        self.regex_hooks = []
        self.sieves = []
        self.cap_hooks = {"on_available": defaultdict(list), "on_ack": defaultdict(list)}
        self.connect_hooks = []
        self.out_sieves = []
        self.hook_hooks = defaultdict(list)
        self.perm_hooks = defaultdict(list)

        self.hook_queue = asyncio.Queue()

        self.running = False

        self._worker = None

    @asyncio.coroutine
    def start(self):
        self.running = True
        self._worker = async_util.wrap_future(self.do_loop())

    @asyncio.coroutine
    def shutdown(self):
        self.running = False
        self.hook_queue.put_nowait(None)

        if self._worker:
            yield from self._worker

    @asyncio.coroutine
    def do_loop(self):
        while self.bot.running:
            task = yield from self.hook_queue.get()
            if task is None:
                continue

            _hook, event = task
            async_util.wrap_future(self.launch(_hook, event))
            self.hook_queue.task_done()
            yield from asyncio.sleep(0)

    def find_plugin(self, title):
        """
        Finds a loaded plugin and returns its Plugin object
        :param title: the title of the plugin to find
        :return: The Plugin object if it exists, otherwise None
        """
        return self._plugin_name_map.get(title)

    @asyncio.coroutine
    def load_all(self, plugin_dir):
        """
        Load a plugin from each *.py file in the given directory.

        Won't load any plugins listed in "disabled_plugins".

        :type plugin_dir: str | Path
        """
        plugin_dir = Path(plugin_dir)
        # Load all .py files in the plugins directory and any subdirectory
        # But ignore files starting with _
        path_list = plugin_dir.rglob("[!_]*.py")
        # Load plugins asynchronously :O
        yield from asyncio.gather(*[self.load_plugin(path) for path in path_list], loop=self.bot.loop)

    @asyncio.coroutine
    def unload_all(self):
        yield from asyncio.gather(
            *[self.unload_plugin(path) for path in self.plugins.keys()], loop=self.bot.loop
        )

    @asyncio.coroutine
    def load_plugin(self, path):
        """
        Loads a plugin from the given path and plugin object, then registers all hooks from that plugin.

        Won't load any plugins listed in "disabled_plugins".

        :type path: str | Path
        """

        path = Path(path)
        file_path = path.resolve()
        file_name = file_path.name
        # Resolve the path relative to the current directory
        plugin_path = file_path.relative_to(self.bot.base_dir)
        title = '.'.join(plugin_path.parts[1:]).rsplit('.', 1)[0]

        if "plugin_loading" in self.bot.config:
            pl = self.bot.config.get("plugin_loading")

            if pl.get("use_whitelist", False):
                if title not in pl.get("whitelist", []):
                    logger.info('Not loading plugin module "{}": plugin not whitelisted'.format(title))
                    return
            else:
                if title in pl.get("blacklist", []):
                    logger.info('Not loading plugin module "{}": plugin blacklisted'.format(title))
                    return

        # make sure to unload the previously loaded plugin from this path, if it was loaded.
        if str(file_path) in self.plugins:
            yield from self.unload_plugin(file_path)

        module_name = "plugins.{}".format(title)
        try:
            plugin_module = importlib.import_module(module_name)
            # if this plugin was loaded before, reload it
            if hasattr(plugin_module, "_cloudbot_loaded"):
                importlib.reload(plugin_module)
        except Exception:
            logger.exception("Error loading {}:".format(title))
            return

        # create the plugin
        plugin = Plugin(str(file_path), file_name, title, plugin_module)

        # proceed to register hooks

        # create database tables
        yield from plugin.create_tables(self.bot)

        # run on_start hooks
        for on_start_hook in plugin.hooks[HookTypes.ONSTART.type]:
            success = yield from self.launch(on_start_hook, Event(bot=self.bot, hook=on_start_hook))
            if not success:
                logger.warning("Not registering hooks from plugin {}: on_start hook errored".format(plugin.title))

                # unregister databases
                plugin.unregister_tables(self.bot)
                return

        self.plugins[plugin.file_path] = plugin
        self._plugin_name_map[plugin.title] = plugin

        for hooks in plugin.hooks.values():
            for _hook in hooks:
                _hook.register(self)

        # Sort hooks
        self.regex_hooks.sort(key=lambda x: x[1].priority)
        dicts_of_lists_of_hooks = (self.event_type_hooks, self.raw_triggers, self.perm_hooks, self.hook_hooks)
        lists_of_hooks = [self.catch_all_triggers, self.sieves, self.connect_hooks, self.out_sieves]
        lists_of_hooks.extend(chain.from_iterable(d.values() for d in dicts_of_lists_of_hooks))

        for lst in lists_of_hooks:
            lst.sort(key=attrgetter("priority"))

        # we don't need this anymore
        del plugin.hooks[HookTypes.ONSTART.type]

    @asyncio.coroutine
    def unload_plugin(self, path):
        """
        Unloads the plugin from the given path, unregistering all hooks from the plugin.

        Returns True if the plugin was unloaded, False if the plugin wasn't loaded in the first place.

        :type path: str | Path
        :rtype: bool
        """
        path = Path(path)
        file_path = path.resolve()

        # make sure this plugin is actually loaded
        if str(file_path) not in self.plugins:
            return False

        # get the loaded plugin
        plugin = self.plugins[str(file_path)]

        for hooks in plugin.hooks.values():
            for _hook in hooks:
                _hook.unregister(self)

        # Run on_stop hooks
        for on_stop_hook in plugin.hooks[HookTypes.ONSTOP.type]:
            event = Event(bot=self.bot, hook=on_stop_hook)
            yield from self.launch(on_stop_hook, event)

        # unregister databases
        plugin.unregister_tables(self.bot)

        task_count = len(plugin.tasks)
        if task_count > 0:
            logger.debug("Cancelling running tasks in %s", plugin.title)
            for task in plugin.tasks:
                task.cancel()

            logger.info("Cancelled %d tasks from %s", task_count, plugin.title)

        # remove last reference to plugin
        del self.plugins[plugin.file_path]

        if self.bot.config.get("logging", {}).get("show_plugin_loading", True):
            logger.info("Unloaded all plugins from {}".format(plugin.title))

        return True

    def _log_hook(self, hook):
        """
        Logs registering a given hook

        :type hook: Hook
        """
        if self.bot.config.get("logging", {}).get("show_plugin_loading", True):
            logger.info("Loaded {}".format(hook))
            logger.debug("Loaded {}".format(repr(hook)))

    @asyncio.coroutine
    def internal_launch(self, hook, event):
        """
        Launches a hook with the data from [event]
        :param hook: The hook to launch
        :param event: The event providing data for the hook
        :return: a tuple of (ok, result) where ok is a boolean that determines if the hook ran without error and result is the result from the hook
        """
        coro = run_func_with_args(self.bot.loop, hook.function, event)

        task = async_util.wrap_future(coro)
        hook.plugin.tasks.append(task)
        try:
            out = yield from task
            ok = True
        except Exception:
            logger.exception("Error in hook {}".format(hook.description))
            ok = False
            out = sys.exc_info()

        hook.plugin.tasks.remove(task)

        return ok, out

    @asyncio.coroutine
    def _wrap_and_run(self, hook, event):
        ok, out = yield from self.internal_launch(hook, event)
        result, error = None, None
        if ok is True:
            result = out
        else:
            error = out

        post_event = partial(
            PostHookEvent, launched_hook=hook, launched_event=event, bot=event.bot,
            conn=event.conn, result=result, error=error
        )
        for post_hook in self.hook_hooks["post"]:
            success, res = yield from self.internal_launch(post_hook, post_event(hook=post_hook))
            if success and res is False:
                break

        return ok, out

    @asyncio.coroutine
    def _execute_hook(self, hook, event):
        """
        Runs the specific hook with the given bot and event.

        Returns False if the hook errored, True otherwise.

        :type hook: cloudbot.plugin.Hook
        :type event: cloudbot.event.Event
        :rtype: bool
        """
        ok, out = yield from self._wrap_and_run(hook, event)

        return ok

    @asyncio.coroutine
    def _sieve(self, sieve, event):
        """
        :type sieve: cloudbot.plugin.Hook
        :type event: cloudbot.event.Event
        :rtype: cloudbot.event.Event
        """
        ok, out = yield from self._wrap_and_run(sieve, event)

        return out if ok else None

    @asyncio.coroutine
    def _start_periodic(self, hook):
        interval = hook.interval
        initial_interval = hook.initial_interval
        yield from asyncio.sleep(initial_interval)

        while True:
            event = Event(bot=self.bot, hook=hook)
            yield from self.launch(hook, event)
            yield from asyncio.sleep(interval)

    @asyncio.coroutine
    def launch_with_sieves(self, hook, event):
        """
        Dispatch a given event to a given hook using a given bot object.

        Returns False if the hook didn't run successfully, and True if it ran successfully.

        :type event: cloudbot.event.Event
        :type hook: cloudbot.hooks.full.Hook
        :rtype: bool
        """

        if event.hook is not hook:
            raise ValueError("Can not launch {!r} with {!r}, hook objects differ.".format(hook, event))

        # we don't need sieves on on_start hooks.
        if hook.type not in (HookTypes.ONSTART.type, HookTypes.ONSTOP.type, HookTypes.PERIODIC.type):
            for sieve in self.bot.plugin_manager.sieves:
                event = yield from self._sieve(sieve, event)
                if event is None:
                    return False

        return (yield from self._execute_hook(hook, event))

    @asyncio.coroutine
    def launch(self, hook, event):
        """
        Dispatch a given event to a given hook using a given bot object.

        Returns False if the hook didn't run successfully, and True if it ran successfully.

        :type event: cloudbot.event.Event
        :type hook: cloudbot.hooks.full.Hook
        :rtype: bool
        """

        if hook.single_thread:
            # There should only be one running instance of this hook, so let's wait for the last event to be processed
            # before starting this one.
            with (yield from hook.lock):
                result = yield from self.launch_with_sieves(hook, event)
        else:
            # Run the plugin with the message, and wait for it to finish
            result = yield from self.launch_with_sieves(hook, event)

        # Return the result
        return result


class Plugin:
    """
    Each Plugin represents a plugin file, and contains loaded hooks.

    :type file_path: str
    :type file_name: str
    :type title: str
    :type hooks: dict
    :type tables: list[sqlalchemy.Table]
    """

    def __init__(self, filepath, filename, title, code):
        """
        :type filepath: str
        :type filename: str
        :type code: object
        """
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

    @asyncio.coroutine
    def create_tables(self, bot):
        """
        Creates all sqlalchemy Tables that are registered in this plugin

        :type bot: cloudbot.bot.CloudBot
        """
        if self.tables:
            # if there are any tables

            logger.info("Registering tables for {}".format(self.title))

            for table in self.tables:
                if not (yield from bot.loop.run_in_executor(None, table.exists, bot.db_engine)):
                    yield from bot.loop.run_in_executor(None, table.create, bot.db_engine)

    def unregister_tables(self, bot):
        """
        Unregisters all sqlalchemy Tables registered to the global metadata by this plugin
        :type bot: cloudbot.bot.CloudBot
        """
        if self.tables:
            # if there are any tables
            logger.info("Unregistering tables for {}".format(self.title))

            for table in self.tables:
                bot.db_metadata.remove(table)
