import asyncio
import importlib
import inspect
import logging
import re
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
        self._hook_waiting_queues = {}

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
    def launch(self, hook, event):
        """
        Dispatch a given event to a given hook using a given bot object.

        Returns False if the hook didn't run successfully, and True if it ran successfully.

        :type event: cloudbot.event.Event
        :type hook: cloudbot.plugin.Hook
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

        if hook.single_thread:
            # There should only be one running instance of this hook, so let's wait for the last event to be processed
            # before starting this one.

            key = (hook.plugin.title, hook.function_name)
            if key in self._hook_waiting_queues:
                queue = self._hook_waiting_queues[key]
                if queue is None:
                    # there's a hook running, but the queue hasn't been created yet, since there's only one hook
                    queue = asyncio.Queue()
                    self._hook_waiting_queues[key] = queue
                assert isinstance(queue, asyncio.Queue)
                # create a future to represent this task
                future = async_util.create_future(self.bot.loop)
                queue.put_nowait(future)
                # wait until the last task is completed
                yield from future
            else:
                # set to None to signify that this hook is running, but there's no need to create a full queue
                # in case there are no more hooks that will wait
                self._hook_waiting_queues[key] = None

            # Run the plugin with the message, and wait for it to finish
            result = yield from self._execute_hook(hook, event)

            queue = self._hook_waiting_queues[key]
            if queue is None or queue.empty():
                # We're the last task in the queue, we can delete it now.
                del self._hook_waiting_queues[key]
            else:
                # set the result for the next task's future, so they can execute
                next_future = yield from queue.get()
                next_future.set_result(None)
        else:
            # Run the plugin with the message, and wait for it to finish
            result = yield from self._execute_hook(hook, event)

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


class Hook:
    """
    Each hook is specific to one function. This class is never used by itself, rather extended.

    :type type; str
    :type plugin: Plugin
    :type function: callable
    :type function_name: str
    :type required_args: list[str]
    :type threaded: bool
    :type permissions: list[str]
    :type single_thread: bool
    """

    def __init__(self, _type, plugin, func_hook):
        """
        :type _type: str
        :type plugin: Plugin
        :type func_hook: hook._Hook
        """
        self.type = _type
        self.plugin = plugin
        self.function = func_hook.function
        self.function_name = self.function.__name__

        sig = inspect.signature(self.function)

        # don't process args starting with "_"
        self.required_args = [arg for arg in sig.parameters.keys() if not arg.startswith('_')]
        if sys.version_info < (3, 7, 0):
            if "async" in self.required_args:
                logger.warning("Use of deprecated function 'async' in %s", self.description)
                time.sleep(1)
                warnings.warn(
                    "event.async() is deprecated, use event.async_call() instead.",
                    DeprecationWarning, stacklevel=2
                )

        if asyncio.iscoroutine(self.function) or asyncio.iscoroutinefunction(self.function):
            self.threaded = False
        else:
            self.threaded = True

        self.permissions = func_hook.kwargs.pop("permissions", [])
        self.single_thread = func_hook.kwargs.pop("singlethread", False)
        self.action = func_hook.kwargs.pop("action", Action.CONTINUE)
        self.priority = func_hook.kwargs.pop("priority", Priority.NORMAL)

        clients = func_hook.kwargs.pop("clients", [])

        if isinstance(clients, str):
            clients = [clients]

        self.clients = clients

        if func_hook.kwargs:
            # we should have popped all the args, so warn if there are any left
            logger.warning("Ignoring extra args {} from {}".format(func_hook.kwargs, self.description))

    @property
    def description(self):
        return "{}:{}".format(self.plugin.title, self.function_name)

    def __repr__(self):
        return "type: {}, plugin: {}, permissions: {}, single_thread: {}, threaded: {}".format(
            self.type, self.plugin.title, self.permissions, self.single_thread, self.threaded
        )


class CommandHook(Hook):
    """
    :type name: str
    :type aliases: list[str]
    :type doc: str
    :type auto_help: bool
    """

    def __init__(self, plugin, cmd_hook):
        """
        :type plugin: Plugin
        :type cmd_hook: cloudbot.util.hook._CommandHook
        """
        self.auto_help = cmd_hook.kwargs.pop("autohelp", True)

        self.name = cmd_hook.main_alias.lower()
        self.aliases = [alias.lower() for alias in cmd_hook.aliases]  # turn the set into a list
        self.aliases.remove(self.name)
        self.aliases.insert(0, self.name)  # make sure the name, or 'main alias' is in position 0
        self.doc = cmd_hook.doc

        super().__init__("command", plugin, cmd_hook)

    def __repr__(self):
        return "Command[name: {}, aliases: {}, {}]".format(self.name, self.aliases[1:], Hook.__repr__(self))

    def __str__(self):
        return "command {} from {}".format("/".join(self.aliases), self.plugin.file_name)


class RegexHook(Hook):
    """
    :type regexes: set[re.__Regex]
    """

    def __init__(self, plugin, regex_hook):
        """
        :type plugin: Plugin
        :type regex_hook: cloudbot.util.hook._RegexHook
        """
        self.run_on_cmd = regex_hook.kwargs.pop("run_on_cmd", False)
        self.only_no_match = regex_hook.kwargs.pop("only_no_match", False)

        self.regexes = regex_hook.regexes

        super().__init__("regex", plugin, regex_hook)

    def __repr__(self):
        return "Regex[regexes: [{}], {}]".format(", ".join(regex.pattern for regex in self.regexes),
                                                 Hook.__repr__(self))

    def __str__(self):
        return "regex {} from {}".format(self.function_name, self.plugin.file_name)


class PeriodicHook(Hook):
    """
    :type interval: int
    """

    def __init__(self, plugin, periodic_hook):
        """
        :type plugin: Plugin
        :type periodic_hook: cloudbot.util.hook._PeriodicHook
        """

        self.interval = periodic_hook.interval
        self.initial_interval = periodic_hook.kwargs.pop("initial_interval", self.interval)

        super().__init__("periodic", plugin, periodic_hook)

    def __repr__(self):
        return "Periodic[interval: [{}], {}]".format(self.interval, Hook.__repr__(self))

    def __str__(self):
        return "periodic hook ({} seconds) {} from {}".format(self.interval, self.function_name, self.plugin.file_name)


class RawHook(Hook):
    """
    :type triggers: set[str]
    """

    def __init__(self, plugin, irc_raw_hook):
        """
        :type plugin: Plugin
        :type irc_raw_hook: cloudbot.util.hook._RawHook
        """
        super().__init__("irc_raw", plugin, irc_raw_hook)

        self.triggers = irc_raw_hook.triggers

    def is_catch_all(self):
        return "*" in self.triggers

    def __repr__(self):
        return "Raw[triggers: {}, {}]".format(list(self.triggers), Hook.__repr__(self))

    def __str__(self):
        return "irc raw {} ({}) from {}".format(self.function_name, ",".join(self.triggers), self.plugin.file_name)


class SieveHook(Hook):
    def __init__(self, plugin, sieve_hook):
        """
        :type plugin: Plugin
        :type sieve_hook: cloudbot.util.hook._SieveHook
        """
        super().__init__("sieve", plugin, sieve_hook)

    def __repr__(self):
        return "Sieve[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "sieve {} from {}".format(self.function_name, self.plugin.file_name)


class EventHook(Hook):
    """
    :type types: set[cloudbot.event.EventType]
    """

    def __init__(self, plugin, event_hook):
        """
        :type plugin: Plugin
        :type event_hook: cloudbot.util.hook._EventHook
        """
        super().__init__("event", plugin, event_hook)

        self.types = event_hook.types

    def __repr__(self):
        return "Event[types: {}, {}]".format(list(self.types), Hook.__repr__(self))

    def __str__(self):
        return "event {} ({}) from {}".format(self.function_name, ",".join(str(t) for t in self.types),
                                              self.plugin.file_name)


class OnStartHook(Hook):
    def __init__(self, plugin, on_start_hook):
        """
        :type plugin: Plugin
        :type on_start_hook: cloudbot.util.hook._On_startHook
        """
        super().__init__("on_start", plugin, on_start_hook)

    def __repr__(self):
        return "On_start[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "on_start {} from {}".format(self.function_name, self.plugin.file_name)


class OnStopHook(Hook):
    def __init__(self, plugin, on_stop_hook):
        super().__init__("on_stop", plugin, on_stop_hook)

    def __repr__(self):
        return "On_stop[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "on_stop {} from {}".format(self.function_name, self.plugin.file_name)


class CapHook(Hook):
    def __init__(self, _type, plugin, base_hook):
        self.caps = base_hook.caps
        super().__init__("on_cap_{}".format(_type), plugin, base_hook)

    def __repr__(self):
        return "{name}[{caps} {base!r}]".format(name=self.type, caps=self.caps, base=super())

    def __str__(self):
        return "{name} {func} from {file}".format(name=self.type, func=self.function_name, file=self.plugin.file_name)


class OnCapAvaliableHook(CapHook):
    def __init__(self, plugin, base_hook):
        super().__init__("available", plugin, base_hook)


class OnCapAckHook(CapHook):
    def __init__(self, plugin, base_hook):
        super().__init__("ack", plugin, base_hook)


class OnConnectHook(Hook):
    def __init__(self, plugin, sieve_hook):
        """
        :type plugin: Plugin
        :type sieve_hook: cloudbot.util.hook._Hook
        """
        super().__init__("on_connect", plugin, sieve_hook)

    def __repr__(self):
        return "{name}[{base!r}]".format(name=self.type, base=super())

    def __str__(self):
        return "{name} {func} from {file}".format(name=self.type, func=self.function_name, file=self.plugin.file_name)


class IrcOutHook(Hook):
    def __init__(self, plugin, out_hook):
        super().__init__("irc_out", plugin, out_hook)

    def __repr__(self):
        return "Irc_Out[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "irc_out {} from {}".format(self.function_name, self.plugin.file_name)


class PostHookHook(Hook):
    def __init__(self, plugin, out_hook):
        super().__init__("post_hook", plugin, out_hook)

    def __repr__(self):
        return "Post_hook[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "post_hook {} from {}".format(self.function_name, self.plugin.file_name)
