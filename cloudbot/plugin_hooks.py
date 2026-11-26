from __future__ import annotations

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from typing_extensions import override

from cloudbot.hook import (
    Action,
    CapFuncHook,
    CommandFuncHook,
    CommandHookKwargs,
    ConfigFuncHook,
    ConnectFuncHook,
    EventFuncHook,
    FuncHook,
    HookKwargs,
    HookType,
    IrcOutFuncHook,
    OnStartFuncHook,
    OnStopFuncHook,
    PeriodicFuncHook,
    PeriodicHookKwargs,
    PermissionFuncHook,
    PostHookFuncHook,
    Priority,
    RawFuncHook,
    RegexFuncHook,
    RegexHookKwargs,
    SieveFuncHook,
)

if TYPE_CHECKING:
    from cloudbot.plugin import Plugin

logger = logging.getLogger("cloudbot")

_KwargsT = TypeVar("_KwargsT", bound=HookKwargs)


class Hook(ABC, Generic[_KwargsT]):
    """
    Each hook is specific to one function. This class is never used by itself,
    rather extended.
    """

    def __init__(
        self, plugin: Plugin, func_hook: FuncHook[_KwargsT], kwargs: _KwargsT
    ) -> None:
        """ """
        self.plugin = plugin
        self.function = func_hook.function
        self.function_name = self.function.__name__

        sig = inspect.signature(self.function)

        # don't process args starting with "_"
        self.required_args = [
            arg for arg in sig.parameters.keys() if not arg.startswith("_")
        ]

        if inspect.iscoroutinefunction(self.function):
            self.threaded = False
        else:
            self.threaded = True

        self.permissions = kwargs.pop("permissions", [])
        self.single_thread = kwargs.pop("singlethread", False)
        self.action = kwargs.pop("action", Action.CONTINUE)
        self.priority: int | Priority = kwargs.pop("priority", Priority.NORMAL)
        self.do_sieve = kwargs.pop("do_sieve", True)

        lock = kwargs.pop("lock", None)

        if self.single_thread and not lock:
            lock = asyncio.Lock()

        self.lock = lock

        clients = kwargs.pop("clients", [])

        if isinstance(clients, str):
            clients = [clients]

        self.clients = clients

        if kwargs:
            # we should have popped all the args, so warn if there are any left
            logger.warning(
                "Ignoring extra args %s from %s",
                func_hook.kwargs,
                self.description,
            )

    @classmethod
    @abstractmethod
    def get_type(cls) -> HookType:
        raise NotImplementedError

    @property
    def type(self) -> HookType:
        return self.get_type()

    @property
    def description(self) -> str:
        return f"{self.plugin.title}:{self.function_name}"

    def __repr__(self) -> str:
        parts = [
            ("type", self.type),
            ("plugin", self.plugin.title),
            ("permissions", self.permissions),
            ("single_thread", self.single_thread),
            ("threaded", self.threaded),
        ]
        return ", ".join(f"{k}: {v}" for k, v in parts)


class CommandHook(Hook[CommandHookKwargs]):
    def __init__(self, plugin: Plugin, cmd_hook: CommandFuncHook) -> None:
        kwargs = cmd_hook.kwargs
        if kwargs is None:
            kwargs = CommandHookKwargs()

        auto_help = kwargs.pop("autohelp", True)

        super().__init__(plugin, cmd_hook, kwargs)

        self.auto_help = auto_help

        if cmd_hook.main_alias is None:
            raise TypeError("Main alias not set on CommandFuncHook")

        self.name = cmd_hook.main_alias.lower()
        # turn the set into a list
        self.aliases = [alias.lower() for alias in cmd_hook.aliases]
        self.aliases.remove(self.name)
        # make sure the name, or 'main alias' is in position 0
        self.aliases.insert(0, self.name)
        self.doc = cmd_hook.doc

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.COMMAND

    def __repr__(self) -> str:
        return f"Command[name: {self.name}, aliases: {self.aliases[1:]}, {super().__repr__()}]"

    def __str__(self) -> str:
        return f"command {'/'.join(self.aliases)} from {self.plugin.file_name}"


class RegexHook(Hook[RegexHookKwargs]):
    def __init__(self, plugin: Plugin, regex_hook: RegexFuncHook) -> None:
        kwargs = regex_hook.kwargs
        if kwargs is None:
            kwargs = RegexHookKwargs()

        run_on_cmd = kwargs.pop("run_on_cmd", False)
        only_no_match = kwargs.pop("only_no_match", False)

        super().__init__(plugin, regex_hook, kwargs)

        self.run_on_cmd = run_on_cmd
        self.only_no_match = only_no_match

        self.regexes = regex_hook.regexes

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.REGEX

    def __repr__(self) -> str:
        return f"Regex[regexes: [{', '.join(regex.pattern for regex in self.regexes)}], {super().__repr__()}]"

    def __str__(self) -> str:
        return f"regex {self.function_name} from {self.plugin.file_name}"


class PeriodicHook(Hook[PeriodicHookKwargs]):
    def __init__(self, plugin: Plugin, periodic_hook: PeriodicFuncHook) -> None:
        kwargs = periodic_hook.kwargs
        if kwargs is None:
            kwargs = PeriodicHookKwargs()

        interval = periodic_hook.interval
        initial_interval = kwargs.pop("initial_interval", interval)

        super().__init__(plugin, periodic_hook, kwargs)

        self.interval = interval
        self.initial_interval = initial_interval

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.PERIODIC

    def __repr__(self) -> str:
        return f"Periodic[interval: [{self.interval}], {super().__repr__()}]"

    def __str__(self) -> str:
        return f"periodic hook ({self.interval} seconds) {self.function_name} from {self.plugin.file_name}"


class RawHook(Hook[HookKwargs]):
    def __init__(self, plugin: Plugin, irc_raw_hook: RawFuncHook) -> None:
        kwargs = irc_raw_hook.kwargs
        if kwargs is None:
            kwargs = HookKwargs()

        super().__init__(plugin, irc_raw_hook, kwargs)

        self.triggers = irc_raw_hook.triggers

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.IRC_RAW

    def is_catch_all(self) -> bool:
        return "*" in self.triggers

    def __repr__(self) -> str:
        return f"Raw[triggers: {list(self.triggers)}, {super().__repr__()}]"

    def __str__(self) -> str:
        return f"irc raw {self.function_name} ({','.join(self.triggers)}) from {self.plugin.file_name}"


class SieveHook(Hook[HookKwargs]):
    def __init__(self, plugin: Plugin, sieve_hook: SieveFuncHook) -> None:
        kwargs = sieve_hook.kwargs
        if kwargs is None:
            kwargs = HookKwargs()

        super().__init__(plugin, sieve_hook, kwargs)

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.SIEVE

    def __repr__(self) -> str:
        return f"Sieve[{super().__repr__()}]"

    def __str__(self) -> str:
        return f"sieve {self.function_name} from {self.plugin.file_name}"


class EventHook(Hook[HookKwargs]):
    def __init__(self, plugin: Plugin, event_hook: EventFuncHook) -> None:
        kwargs = event_hook.kwargs
        if kwargs is None:
            kwargs = HookKwargs()

        super().__init__(plugin, event_hook, kwargs)

        self.types = event_hook.types

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.EVENT

    def __repr__(self) -> str:
        return f"Event[types: {list(self.types)}, {super().__repr__()}]"

    def __str__(self) -> str:
        return f"event {self.function_name} ({','.join(str(t) for t in self.types)}) from {self.plugin.file_name}"


class OnStartHook(Hook[HookKwargs]):
    def __init__(self, plugin: Plugin, on_start_hook: OnStartFuncHook) -> None:
        """ """
        kwargs = on_start_hook.kwargs
        if kwargs is None:
            kwargs = HookKwargs()

        super().__init__(plugin, on_start_hook, kwargs)

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.ON_START

    def __repr__(self) -> str:
        return f"On_start[{super().__repr__()}]"

    def __str__(self) -> str:
        return f"on_start {self.function_name} from {self.plugin.file_name}"


class OnStopHook(Hook[HookKwargs]):
    def __init__(self, plugin: Plugin, on_stop_hook: OnStopFuncHook) -> None:
        kwargs = on_stop_hook.kwargs
        if kwargs is None:
            kwargs = HookKwargs()

        super().__init__(plugin, on_stop_hook, kwargs)

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.ON_STOP

    def __repr__(self) -> str:
        return f"On_stop[{super().__repr__()}]"

    def __str__(self) -> str:
        return f"on_stop {self.function_name} from {self.plugin.file_name}"


class CapHook(Hook[HookKwargs], ABC):
    def __init__(self, plugin: Plugin, base_hook: CapFuncHook) -> None:
        kwargs = base_hook.kwargs
        if kwargs is None:
            kwargs = HookKwargs()

        super().__init__(plugin, base_hook, kwargs)

        self.caps = base_hook.caps

    def __repr__(self) -> str:
        return f"{self.type}[{self.caps} {super()!r}]"

    def __str__(self) -> str:
        return f"{self.type} {self.function_name} from {self.plugin.file_name}"


class OnCapAvailableHook(CapHook):
    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.CAP_AVAILABLE


OnCapAvaliableHook = OnCapAvailableHook


class OnCapAckHook(CapHook):
    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.CAP_ACK


class OnConnectHook(Hook[HookKwargs]):
    def __init__(self, plugin: Plugin, sieve_hook: ConnectFuncHook) -> None:
        """ """
        kwargs = sieve_hook.kwargs
        if kwargs is None:
            kwargs = HookKwargs()

        super().__init__(plugin, sieve_hook, kwargs)

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.CONNECT

    def __repr__(self) -> str:
        return f"{self.type}[{super()!r}]"

    def __str__(self) -> str:
        return f"{self.type} {self.function_name} from {self.plugin.file_name}"


class IrcOutHook(Hook[HookKwargs]):
    def __init__(self, plugin: Plugin, out_hook: IrcOutFuncHook) -> None:
        kwargs = out_hook.kwargs
        if kwargs is None:
            kwargs = HookKwargs()

        super().__init__(plugin, out_hook, kwargs)

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.IRC_OUT

    def __repr__(self) -> str:
        return f"Irc_Out[{super().__repr__()}]"

    def __str__(self) -> str:
        return f"irc_out {self.function_name} from {self.plugin.file_name}"


class PostHookHook(Hook[HookKwargs]):
    def __init__(self, plugin: Plugin, out_hook: PostHookFuncHook) -> None:
        kwargs = out_hook.kwargs
        if kwargs is None:
            kwargs = HookKwargs()

        super().__init__(plugin, out_hook, kwargs)

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.POST_HOOK

    def __repr__(self) -> str:
        return f"Post_hook[{super().__repr__()}]"

    def __str__(self) -> str:
        return f"post_hook {self.function_name} from {self.plugin.file_name}"


class ConfigHook(Hook[HookKwargs]):
    def __init__(self, plugin: Plugin, out_hook: ConfigFuncHook) -> None:
        kwargs = out_hook.kwargs
        if kwargs is None:
            kwargs = HookKwargs()

        super().__init__(plugin, out_hook, kwargs)

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.CONFIG

    def __repr__(self) -> str:
        return f"ConfigHook[{super().__repr__()}]"

    def __str__(self) -> str:
        return f"Config hook {self.function_name} from {self.plugin.file_name}"


class PermHook(Hook[HookKwargs]):
    def __init__(self, plugin: Plugin, perm_hook: PermissionFuncHook) -> None:
        kwargs = perm_hook.kwargs
        if kwargs is None:
            kwargs = HookKwargs()

        super().__init__(plugin, perm_hook, kwargs)

        self.perms = perm_hook.perms

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.PERMISSION

    def __repr__(self) -> str:
        return f"PermHook[{super().__repr__()}]"

    def __str__(self) -> str:
        return f"perm hook {self.function_name} from {self.plugin.file_name}"


_hook_name_to_plugin = {
    HookType.COMMAND: CommandHook,
    HookType.REGEX: RegexHook,
    HookType.IRC_RAW: RawHook,
    HookType.SIEVE: SieveHook,
    HookType.EVENT: EventHook,
    HookType.PERIODIC: PeriodicHook,
    HookType.ON_START: OnStartHook,
    HookType.ON_STOP: OnStopHook,
    HookType.CAP_AVAILABLE: OnCapAvailableHook,
    HookType.CAP_ACK: OnCapAckHook,
    HookType.CONNECT: OnConnectHook,
    HookType.IRC_OUT: IrcOutHook,
    HookType.POST_HOOK: PostHookHook,
    HookType.PERMISSION: PermHook,
    HookType.CONFIG: ConfigHook,
}

hook_name_to_plugin = _hook_name_to_plugin.__getitem__
