import asyncio
import inspect
import logging
import sys
import warnings
from abc import abstractmethod, ABC

from cloudbot.hook import Action, Priority
from cloudbot.util import async_util

logger = logging.getLogger("cloudbot")


class Hook(ABC):
    """
    Each hook is specific to one function. This class is never used by itself, rather extended.

    :type type; str
    :type plugin: Plugin
    :type function: callable
    :type function_name: str
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
        if sys.version_info < (3, 7, 0):
            if "async" in sig.parameters:
                logger.warning("Use of deprecated function 'async' in %s", self.description)
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

    @abstractmethod
    def register(self, manager):
        """
        :type manager: cloudbot.plugin.PluginManager
        """
        raise NotImplementedError

    @abstractmethod
    def unregister(self, manager):
        """
        :type manager: cloudbot.plugin.PluginManager
        """
        raise NotImplementedError


class HookListRegister(Hook):
    @abstractmethod
    def get_list(self, manager):
        raise NotImplementedError

    def register(self, manager):
        self.get_list(manager).append(self)
        manager._log_hook(self)

    def unregister(self, manager):
        self.get_list(manager).remove(self)


class CommandHook(Hook):
    """
    :type name: str
    :type aliases: list[str]
    :type doc: str
    :type auto_help: bool
    """

    def register(self, manager):
        for alias in self.aliases:
            if alias in manager.commands:
                logger.warning(
                    "Plugin {} attempted to register command {} which was already registered by {}. "
                    "Ignoring new assignment.".format(self.plugin.title, alias, manager.commands[alias].plugin.title))
            else:
                manager.commands[alias] = self

        manager._log_hook(self)

    def unregister(self, manager):
        for alias in self.aliases:
            if alias in manager.commands and manager.commands[alias] is self:
                # we need to make sure that there wasn't a conflict, so we don't delete another plugin's command
                del manager.commands[alias]

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

    def register(self, manager):
        for regex_match in self.regexes:
            manager.regex_hooks.append((regex_match, self))

        manager._log_hook(self)

    def unregister(self, manager):
        for regex_match in self.regexes:
            manager.regex_hooks.remove((regex_match, self))

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

    def register(self, manager):
        task = async_util.wrap_future(manager._start_periodic(self))
        self.plugin.tasks.append(task)
        manager._log_hook(self)

    def unregister(self, manager):
        pass

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

    def register(self, manager):
        if self.is_catch_all():
            manager.catch_all_triggers.append(self)
        else:
            for trigger in self.triggers:
                if trigger in manager.raw_triggers:
                    manager.raw_triggers[trigger].append(self)
                else:
                    manager.raw_triggers[trigger] = [self]
        manager._log_hook(self)

    def unregister(self, manager):
        if self.is_catch_all():
            manager.catch_all_triggers.remove(self)
        else:
            for trigger in self.triggers:
                assert trigger in manager.raw_triggers  # this can't be not true
                manager.raw_triggers[trigger].remove(self)
                if not manager.raw_triggers[trigger]:  # if that was the last hook for this trigger
                    del manager.raw_triggers[trigger]

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


class SieveHook(HookListRegister):
    def get_list(self, manager):
        return manager.sieves

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

    def register(self, manager):
        for event_type in self.types:
            if event_type in manager.event_type_hooks:
                manager.event_type_hooks[event_type].append(self)
            else:
                manager.event_type_hooks[event_type] = [self]
        manager._log_hook(self)

    def unregister(self, manager):
        for event_type in self.types:
            assert event_type in manager.event_type_hooks  # this can't be not true
            manager.event_type_hooks[event_type].remove(self)
            if not manager.event_type_hooks[event_type]:  # if that was the last hook for this event type
                del manager.event_type_hooks[event_type]

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
    def register(self, manager):
        pass

    def unregister(self, manager):
        pass

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
    def register(self, manager):
        pass

    def unregister(self, manager):
        pass

    def __init__(self, plugin, on_stop_hook):
        super().__init__("on_stop", plugin, on_stop_hook)

    def __repr__(self):
        return "On_stop[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "on_stop {} from {}".format(self.function_name, self.plugin.file_name)


class CapHook(Hook):
    def register(self, manager):
        for cap in self.caps:
            manager.cap_hooks["on_available"][cap.casefold()].append(self)

        manager._log_hook(self)

    def unregister(self, manager):
        ack_hooks = manager.cap_hooks[self._subtype]
        for cap in self.caps:
            cap_cf = cap.casefold()
            ack_hooks[cap_cf].remove(self)
            if not ack_hooks[cap_cf]:
                del ack_hooks[cap_cf]

    def __init__(self, _type, plugin, base_hook):
        self.caps = base_hook.caps
        self._subtype = _type
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


class OnConnectHook(HookListRegister):
    def get_list(self, manager):
        return manager.connect_hooks

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


class IrcOutHook(HookListRegister):
    def get_list(self, manager):
        return manager.out_sieves

    def __init__(self, plugin, out_hook):
        super().__init__("irc_out", plugin, out_hook)

    def __repr__(self):
        return "Irc_Out[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "irc_out {} from {}".format(self.function_name, self.plugin.file_name)


class PostHookHook(HookListRegister):
    def get_list(self, manager):
        return manager.hook_hooks["post"]

    def __init__(self, plugin, out_hook):
        super().__init__("post_hook", plugin, out_hook)

    def __repr__(self):
        return "Post_hook[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "post_hook {} from {}".format(self.function_name, self.plugin.file_name)


class PermHook(Hook):
    def register(self, manager):
        for perm in self.perms:
            manager.perm_hooks[perm].append(self)

        manager._log_hook(self)

    def unregister(self, manager):
        for perm in self.perms:
            manager.perm_hooks[perm].remove(self)

    def __init__(self, plugin, perm_hook):
        self.perms = perm_hook.perms
        super().__init__("perm_check", plugin, perm_hook)

    def __repr__(self):
        return "PermHook[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "perm hook {} from {}".format(self.function_name, self.plugin.file_name)
