import asyncio
import inspect
import logging

from cloudbot.hook import Action, Priority

logger = logging.getLogger("cloudbot")


class Hook:
    """
    Each hook is specific to one function. This class is never used by itself,
    rather extended.

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
        self.required_args = [
            arg for arg in sig.parameters.keys() if not arg.startswith("_")
        ]

        if asyncio.iscoroutine(self.function) or asyncio.iscoroutinefunction(
            self.function
        ):
            self.threaded = False
        else:
            self.threaded = True

        self.permissions = func_hook.kwargs.pop("permissions", [])
        self.single_thread = func_hook.kwargs.pop("singlethread", False)
        self.action = func_hook.kwargs.pop("action", Action.CONTINUE)
        self.priority = func_hook.kwargs.pop("priority", Priority.NORMAL)
        self.do_sieve = func_hook.kwargs.pop("do_sieve", True)

        lock = func_hook.kwargs.pop("lock", None)

        if self.single_thread and not lock:
            lock = asyncio.Lock()

        self.lock = lock

        clients = func_hook.kwargs.pop("clients", [])

        if isinstance(clients, str):
            clients = [clients]

        self.clients = clients

        if func_hook.kwargs:
            # we should have popped all the args, so warn if there are any left
            logger.warning(
                "Ignoring extra args %s from %s", func_hook.kwargs, self.description
            )

    @property
    def description(self):
        return "{}:{}".format(self.plugin.title, self.function_name)

    def __repr__(self):
        parts = [
            ("type", self.type),
            ("plugin", self.plugin.title),
            ("permissions", self.permissions),
            ("single_thread", self.single_thread),
            ("threaded", self.threaded),
        ]
        return ", ".join("{}: {}".format(k, v) for k, v in parts)


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
        auto_help = cmd_hook.kwargs.pop("autohelp", True)

        super().__init__("command", plugin, cmd_hook)

        self.auto_help = auto_help

        self.name = cmd_hook.main_alias.lower()
        self.aliases = [
            alias.lower() for alias in cmd_hook.aliases
        ]  # turn the set into a list
        self.aliases.remove(self.name)
        self.aliases.insert(
            0, self.name
        )  # make sure the name, or 'main alias' is in position 0
        self.doc = cmd_hook.doc

    def __repr__(self):
        return "Command[name: {}, aliases: {}, {}]".format(
            self.name, self.aliases[1:], Hook.__repr__(self)
        )

    def __str__(self):
        return "command {} from {}".format(
            "/".join(self.aliases), self.plugin.file_name
        )


class RegexHook(Hook):
    """
    :type regexes: set[re.__Regex]
    """

    def __init__(self, plugin, regex_hook):
        """
        :type plugin: Plugin
        :type regex_hook: cloudbot.util.hook._RegexHook
        """
        run_on_cmd = regex_hook.kwargs.pop("run_on_cmd", False)
        only_no_match = regex_hook.kwargs.pop("only_no_match", False)

        super().__init__("regex", plugin, regex_hook)

        self.run_on_cmd = run_on_cmd
        self.only_no_match = only_no_match

        self.regexes = regex_hook.regexes

    def __repr__(self):
        return "Regex[regexes: [{}], {}]".format(
            ", ".join(regex.pattern for regex in self.regexes), Hook.__repr__(self)
        )

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

        interval = periodic_hook.interval
        initial_interval = periodic_hook.kwargs.pop("initial_interval", interval)

        super().__init__("periodic", plugin, periodic_hook)

        self.interval = interval
        self.initial_interval = initial_interval

    def __repr__(self):
        return "Periodic[interval: [{}], {}]".format(self.interval, Hook.__repr__(self))

    def __str__(self):
        return "periodic hook ({} seconds) {} from {}".format(
            self.interval, self.function_name, self.plugin.file_name
        )


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
        return "irc raw {} ({}) from {}".format(
            self.function_name, ",".join(self.triggers), self.plugin.file_name
        )


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
        return "event {} ({}) from {}".format(
            self.function_name,
            ",".join(str(t) for t in self.types),
            self.plugin.file_name,
        )


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
        super().__init__("on_cap_{}".format(_type), plugin, base_hook)

        self.caps = base_hook.caps

    def __repr__(self):
        return "{name}[{caps} {base!r}]".format(
            name=self.type, caps=self.caps, base=super()
        )

    def __str__(self):
        return "{name} {func} from {file}".format(
            name=self.type, func=self.function_name, file=self.plugin.file_name
        )


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
        return "{name} {func} from {file}".format(
            name=self.type, func=self.function_name, file=self.plugin.file_name
        )


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


class PermHook(Hook):
    def __init__(self, plugin, perm_hook):
        super().__init__("perm_check", plugin, perm_hook)

        self.perms = perm_hook.perms

    def __repr__(self):
        return "PermHook[{}]".format(Hook.__repr__(self))

    def __str__(self):
        return "perm hook {} from {}".format(self.function_name, self.plugin.file_name)


_hook_name_to_plugin = {
    "command": CommandHook,
    "regex": RegexHook,
    "irc_raw": RawHook,
    "sieve": SieveHook,
    "event": EventHook,
    "periodic": PeriodicHook,
    "on_start": OnStartHook,
    "on_stop": OnStopHook,
    "on_cap_available": OnCapAvaliableHook,
    "on_cap_ack": OnCapAckHook,
    "on_connect": OnConnectHook,
    "irc_out": IrcOutHook,
    "post_hook": PostHookHook,
    "perm_check": PermHook,
}

hook_name_to_plugin = _hook_name_to_plugin.__getitem__
