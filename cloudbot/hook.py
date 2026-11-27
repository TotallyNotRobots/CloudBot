from __future__ import annotations

import inspect
import re
import warnings
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from copy import copy
from dataclasses import dataclass, field
from enum import Enum, IntEnum, StrEnum, unique
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Literal,
    NotRequired,
    Self,
    TypedDict,
    TypeVar,
    cast,
    overload,
)

from typing_extensions import ParamSpec, Unpack, deprecated, override

from cloudbot.event import EventType
from cloudbot.util import HOOK_ATTR

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Sequence
    from re import Pattern

_T = TypeVar("_T")
_P = ParamSpec("_P")
HookFunc = Callable[..., Any]
valid_command_re = re.compile(r"^\w+$")


@unique
class Priority(IntEnum):
    # Reversed to maintain compatibility with sieve hooks numeric priority
    LOWEST = 127
    LOW = 63
    NORMAL = 0
    HIGH = -64
    HIGHEST = -128


@unique
class Action(Enum):
    """Defines the action to take after executing a hook"""

    # Once this hook executes, no other hook of that type should run
    HALTTYPE = 0
    # Once this hook executes, No other hook should run
    HALTALL = 1
    # Normal execution of all hooks
    CONTINUE = 2


class HookKwargs(TypedDict):
    permissions: NotRequired[list[str]]
    singlethread: NotRequired[bool]
    action: NotRequired[Action]
    priority: NotRequired[Priority | int]
    do_sieve: NotRequired[bool]
    lock: NotRequired[asyncio.Lock]
    clients: NotRequired[list[str] | str]


class CommandHookKwargs(HookKwargs):
    autohelp: NotRequired[bool]


class RegexHookKwargs(HookKwargs):
    only_no_match: NotRequired[bool]
    run_on_cmd: NotRequired[bool]


class PeriodicHookKwargs(HookKwargs):
    initial_interval: NotRequired[float]


_KwargsT = TypeVar("_KwargsT", bound=HookKwargs)


class HookType(StrEnum):
    COMMAND = "command"
    REGEX = "regex"
    SIEVE = "sieve"
    IRC_RAW = "irc_raw"
    PERIODIC = "periodic"
    CONFIG = "config"
    ON_START = "on_start"
    ON_STOP = "on_stop"
    EVENT = "event"
    PERMISSION = "perm_check"
    POST_HOOK = "post_hook"
    CONNECT = "on_connect"
    IRC_OUT = "irc_out"
    CAP_AVAILABLE = "on_cap_available"
    CAP_ACK = "on_cap_ack"


_HookT = TypeVar("_HookT", bound="FuncHook[Any]")


@dataclass
class Hooks:
    _hooks: dict[HookType, FuncHook[Any]] = field(default_factory=dict)

    def get_types(self) -> list[HookType]:
        return list(self._hooks.keys())

    def get(self, hook_cls: type[_HookT]) -> _HookT | None:
        return cast("_HookT", self._hooks.get(hook_cls.get_type()))

    def set(self, hook: FuncHook[Any]) -> None:
        self._hooks[hook.type] = hook

    @classmethod
    def ensure_present(cls, func: HookFunc) -> Self:
        try:
            out = getattr(func, HOOK_ATTR)  # pyright: ignore[reportAny]
        except AttributeError:
            out = cls()
            setattr(func, HOOK_ATTR, out)
            return out
        else:
            if not isinstance(out, cls):
                raise TypeError(
                    f"Found unexpected type in {HOOK_ATTR}: {type(out)}"  # pyright: ignore[reportAny]
                )

            return out

    def items(self) -> Iterable[tuple[HookType, FuncHook[Any]]]:
        return self._hooks.items()

    @classmethod
    def get_from_func(cls, func: HookFunc) -> Self | None:
        try:
            out = getattr(func, HOOK_ATTR)  # pyright: ignore[reportAny]
        except AttributeError:
            return None

        if hasattr(func, f"_not_{HOOK_ATTR}"):
            # Found a weird object that always returns true for hasattr(), ignore it
            return None

        if not isinstance(out, cls):
            raise TypeError(
                f"Found unexpected type in {HOOK_ATTR}: {type(out)}"  # pyright: ignore[reportAny]
            )

        return out

    @classmethod
    def pop_from_func(cls, func: HookFunc) -> Self | None:
        out = cls.get_from_func(func)
        if out is not None:
            delattr(func, HOOK_ATTR)

        return out


class FuncHook(ABC, Generic[_KwargsT]):
    def __init__(self, function: HookFunc) -> None:
        self.function: HookFunc = function
        self.kwargs: _KwargsT | None = None

    @classmethod
    @abstractmethod
    def get_type(cls) -> HookType:
        raise NotImplementedError

    @classmethod
    @overload
    def get_hook(
        cls, func: HookFunc, *, raise_on_missing: Literal[True]
    ) -> Self: ...

    @classmethod
    @overload
    def get_hook(
        cls, func: HookFunc, *, raise_on_missing: Literal[False] = False
    ) -> Self | None: ...

    @classmethod
    def get_hook(
        cls, func: HookFunc, *, raise_on_missing: bool = False
    ) -> Self | None:
        if (hooks := Hooks.get_from_func(func)) is not None:
            hook = hooks.get(cls)
            if hook is not None:
                return hook

        if raise_on_missing:
            raise ValueError(f"Missing hook for {cls.get_type()}")

        return None

    @classmethod
    def get_or_add_hook(cls, func: HookFunc) -> Self:
        hooks = Hooks.ensure_present(func)
        if (hook := hooks.get(cls)) is not None:
            return hook

        hook = cls(func)
        hooks.set(hook)
        return hook

    @property
    def type(self) -> HookType:
        return self.get_type()

    def _add_hook(self, kwargs: _KwargsT) -> None:
        # update kwargs, overwriting duplicates
        if self.kwargs is None:
            self.kwargs = copy(kwargs)
        else:
            self.kwargs.update(kwargs)


class CommandFuncHook(FuncHook[CommandHookKwargs]):
    def __init__(self, function: HookFunc) -> None:
        super().__init__(function)
        self.aliases = set[str]()
        self.main_alias: str | None = None

        if function.__doc__:
            # Split on the first entirely blank line
            self.doc: str | None = " ".join(
                inspect.cleandoc(function.__doc__)
                .split("\n\n", 1)[0]
                .strip("\n")
                .split("\n")
            ).strip()
        else:
            self.doc = None

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.COMMAND

    def add_hook(
        self, alias_param: Sequence[str] | None, kwargs: CommandHookKwargs
    ) -> None:
        self._add_hook(kwargs)

        if not alias_param:
            alias_param = self.function.__name__
        if isinstance(alias_param, str):
            alias_param = [alias_param]
        if not self.main_alias:
            self.main_alias = alias_param[0]
        for alias in alias_param:
            if not valid_command_re.match(alias):
                raise ValueError(f"Invalid command name {alias}")
        self.aliases.update(alias_param)


class RegexFuncHook(FuncHook[RegexHookKwargs]):
    def __init__(self, function: HookFunc) -> None:
        super().__init__(function)
        self.regexes: list[Pattern[str]] = []

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.REGEX

    def add_hook(
        self,
        regex_param: list[re.Pattern[str] | str] | re.Pattern[str] | str,
        kwargs: RegexHookKwargs,
    ) -> None:
        self._add_hook(kwargs)
        # add all regex_parameters to valid regexes
        if isinstance(regex_param, str):
            # if the parameter is a string, compile and add
            self.regexes.append(re.compile(regex_param))
        elif isinstance(regex_param, re.Pattern):
            self.regexes.append(regex_param)
        else:
            # if the parameter is a list, add each one
            for re_to_match in regex_param:
                if isinstance(re_to_match, str):
                    re_to_match = re.compile(re_to_match)

                self.regexes.append(re_to_match)


class SieveFuncHook(FuncHook[HookKwargs]):
    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.SIEVE


class RawFuncHook(FuncHook[HookKwargs]):
    def __init__(self, function: HookFunc) -> None:
        super().__init__(function)
        self.triggers = set[str]()

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.IRC_RAW

    def add_hook(
        self, trigger_param: list[str] | str, kwargs: HookKwargs
    ) -> None:
        self._add_hook(kwargs)

        if isinstance(trigger_param, str):
            self.triggers.add(trigger_param)
        else:
            # it's a list
            self.triggers.update(trigger_param)


class PeriodicFuncHook(FuncHook[PeriodicHookKwargs]):
    def __init__(self, function: HookFunc) -> None:
        super().__init__(function)
        self.interval = 60.0

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.PERIODIC

    def add_hook(self, interval: float, kwargs: PeriodicHookKwargs) -> None:
        self._add_hook(kwargs)

        if interval:
            self.interval = interval


class ConfigFuncHook(FuncHook[HookKwargs]):
    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.CONFIG


class OnStartFuncHook(FuncHook[HookKwargs]):
    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.ON_START


class OnStopFuncHook(FuncHook[HookKwargs]):
    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.ON_STOP


class EventFuncHook(FuncHook[HookKwargs]):
    def __init__(self, function: HookFunc) -> None:
        super().__init__(function)
        self.types = set[EventType]()

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.EVENT

    def add_hook(
        self, trigger_param: EventType | list[EventType], kwargs: HookKwargs
    ) -> None:
        self._add_hook(kwargs)

        if isinstance(trigger_param, EventType):
            self.types.add(trigger_param)
        else:
            # it's a list
            self.types.update(trigger_param)


class CapFuncHook(FuncHook[HookKwargs], ABC):
    def __init__(self, func: HookFunc) -> None:
        super().__init__(func)
        self.caps = set[str]()

    def add_hook(self, caps: tuple[str, ...], kwargs: HookKwargs) -> None:
        self._add_hook(kwargs)
        self.caps.update(caps)


class CapAvailableFuncHook(CapFuncHook):
    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.CAP_AVAILABLE


class CapAckFuncHook(CapFuncHook):
    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.CAP_ACK


class ConnectFuncHook(FuncHook[HookKwargs]):
    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.CONNECT


class IrcOutFuncHook(FuncHook[HookKwargs]):
    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.IRC_OUT


class PostHookFuncHook(FuncHook[HookKwargs]):
    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.POST_HOOK


class PermissionFuncHook(FuncHook[HookKwargs]):
    def __init__(self, func: HookFunc) -> None:
        super().__init__(func)
        self.perms = set[str]()

    @classmethod
    @override
    def get_type(cls) -> HookType:
        return HookType.PERMISSION

    def add_hook(self, perms: Sequence[str], kwargs: HookKwargs) -> None:
        self._add_hook(kwargs)
        self.perms.update(perms)


def _hook_warn() -> None:
    warnings.warn(
        "Direct decorators are deprecated", DeprecationWarning, stacklevel=3
    )


@dataclass
class _HookDecorator(ABC, Generic[_KwargsT]):
    kwargs: _KwargsT

    @abstractmethod
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        raise NotImplementedError


@dataclass
class _CommandDecorator(_HookDecorator[CommandHookKwargs]):
    alias_param: Sequence[str] | None

    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        hook = CommandFuncHook.get_or_add_hook(func)
        hook.add_hook(self.alias_param, self.kwargs)
        return func


@overload
@deprecated(
    "Bare decorators are deprecated, use @command() instead of @command",
    category=DeprecationWarning,
)
def command(arg: Callable[_P, _T], /) -> Callable[_P, _T]: ...


@overload
def command(
    arg: str | Sequence[str] | None = None,
    /,
    *args: str,
    **kwargs: Unpack[CommandHookKwargs],
) -> _CommandDecorator: ...


def command(
    arg: Callable[_P, _T] | str | Sequence[str] | None = None,
    /,
    *args: str | Sequence[str],
    **kwargs: Unpack[CommandHookKwargs],
) -> Callable[_P, _T] | _CommandDecorator:
    """External command decorator. Can be used directly as a decorator, or with args to return a decorator."""

    if callable(arg):
        # this decorator is being used directly
        _hook_warn()
        return _CommandDecorator(alias_param=None, kwargs={})(arg)

    arg_list: list[str] = []
    if arg:
        args = (arg, *args)

    for item in args:
        if isinstance(item, str):
            arg_list.append(item)
        else:
            arg_list.extend(item)

    # this decorator is being used indirectly, so return a decorator function
    return _CommandDecorator(alias_param=arg_list, kwargs=kwargs)


@dataclass
class _RawDecorator(_HookDecorator[HookKwargs]):
    triggers_param: list[str] | str

    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        hook = RawFuncHook.get_or_add_hook(func)
        hook.add_hook(self.triggers_param, self.kwargs)
        return func


def irc_raw(
    triggers_param: str | list[str], **kwargs: Unpack[HookKwargs]
) -> _RawDecorator:
    """External raw decorator. Must be used as a function to return a decorator"""

    if callable(triggers_param):
        # this decorator is being used directly, which isn't good
        raise TypeError(
            "@irc_raw() must be used as a function that returns a decorator"
        )

    # this decorator is being used as a function, so return a decorator
    return _RawDecorator(triggers_param=triggers_param, kwargs=kwargs)


@dataclass
class _EventDecorator(_HookDecorator[HookKwargs]):
    types_param: list[EventType] | EventType

    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        hook = EventFuncHook.get_or_add_hook(func)
        hook.add_hook(self.types_param, self.kwargs)
        return func


def event(
    types_param: EventType | list[EventType], **kwargs: Unpack[HookKwargs]
) -> _EventDecorator:
    """External event decorator. Must be used as a function to return a decorator"""

    if callable(types_param):
        # this decorator is being used directly, which isn't good
        raise TypeError(
            "@irc_raw() must be used as a function that returns a decorator"
        )

    # this decorator is being used as a function, so return a decorator
    return _EventDecorator(types_param=types_param, kwargs=kwargs)


@dataclass
class _RegexDecorator(_HookDecorator[RegexHookKwargs]):
    regex_param: list[re.Pattern[str] | str] | re.Pattern[str] | str

    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        hook = RegexFuncHook.get_or_add_hook(func)
        hook.add_hook(self.regex_param, self.kwargs)
        return func


def regex(
    regex_param: list[re.Pattern[str] | str] | re.Pattern[str] | str,
    **kwargs: Unpack[RegexHookKwargs],
) -> _RegexDecorator:
    """External regex decorator. Must be used as a function to return a decorator."""

    if callable(regex_param):
        # this decorator is being used directly, which isn't good
        raise TypeError(
            "@regex() hook must be used as a function that returns a decorator"
        )

    # this decorator is being used as a function, so return a decorator
    return _RegexDecorator(kwargs=kwargs, regex_param=regex_param)


@dataclass
class _SieveDecorator(_HookDecorator[HookKwargs]):
    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        if len(inspect.signature(func).parameters) != 3:
            raise ValueError(
                "Sieve hook has incorrect argument count. Needs params: bot, input, plugin"
            )

        hook = SieveFuncHook.get_or_add_hook(func)
        hook._add_hook(self.kwargs)
        return func


@overload
@deprecated(
    "Bare decorators are deprecated, use @sieve() instead of @sieve",
    category=DeprecationWarning,
)
def sieve(param: Callable[_P, _T], /) -> Callable[_P, _T]: ...


@overload
def sieve(**kwargs: Unpack[HookKwargs]) -> _SieveDecorator: ...


def sieve(
    param: Callable[_P, _T] | None = None, /, **kwargs: Unpack[HookKwargs]
) -> _SieveDecorator | Callable[_P, _T]:
    """External sieve decorator. Can be used directly as a decorator, or with args to return a decorator"""

    if callable(param):
        _hook_warn()
        return _SieveDecorator(kwargs=kwargs)(param)

    return _SieveDecorator(kwargs=kwargs)


@dataclass
class _PeriodicDecorator(_HookDecorator[PeriodicHookKwargs]):
    interval: float

    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        hook = PeriodicFuncHook.get_or_add_hook(func)
        hook.add_hook(self.interval, self.kwargs)
        return func


def periodic(
    interval: float, **kwargs: Unpack[PeriodicHookKwargs]
) -> _PeriodicDecorator:
    """External on_start decorator. Can be used directly as a decorator, or with args to return a decorator"""

    if callable(interval):
        # this decorator is being used directly, which isn't good
        raise TypeError(
            "@periodic() hook must be used as a function that returns a decorator"
        )

    # this decorator is being used as a function, so return a decorator
    return _PeriodicDecorator(interval=interval, kwargs=kwargs)


class _ConfigDecorator(_HookDecorator[HookKwargs]):
    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        hook = ConfigFuncHook.get_or_add_hook(func)
        hook._add_hook(self.kwargs)
        return func


def config(**kwargs: Unpack[HookKwargs]) -> _ConfigDecorator:
    return _ConfigDecorator(kwargs=kwargs)


@dataclass
class _OnStartDecorator(_HookDecorator[HookKwargs]):
    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        hook = OnStartFuncHook.get_or_add_hook(func)
        hook._add_hook(self.kwargs)
        return func


@overload
def on_start(**kwargs: Unpack[HookKwargs]) -> _OnStartDecorator: ...


@overload
@deprecated(
    "Bare decorators are deprecated, use @on_start() instead of @on_start",
    category=DeprecationWarning,
)
def on_start(param: Callable[_P, _T], /) -> Callable[_P, _T]: ...


def on_start(
    param: Callable[_P, _T] | None = None, /, **kwargs: Unpack[HookKwargs]
) -> Callable[_P, _T] | _OnStartDecorator:
    """External on_start decorator. Can be used directly as a decorator, or with args to return a decorator"""

    if callable(param):
        _hook_warn()
        return _OnStartDecorator(kwargs=kwargs)(param)

    return _OnStartDecorator(kwargs=kwargs)


@dataclass
class _OnStopDecorator(_HookDecorator[HookKwargs]):
    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        hook = OnStopFuncHook.get_or_add_hook(func)
        hook._add_hook(self.kwargs)
        return func


@overload
def on_stop(**kwargs: Unpack[HookKwargs]) -> _OnStopDecorator: ...


@overload
@deprecated(
    "Bare decorators are deprecated, use @on_stop() instead of @on_stop",
    category=DeprecationWarning,
)
def on_stop(param: Callable[_P, _T], /) -> Callable[_P, _T]: ...


def on_stop(
    param: Callable[_P, _T] | None = None, /, **kwargs: Unpack[HookKwargs]
) -> Callable[_P, _T] | _OnStopDecorator:
    """External on_stop decorator. Can be used directly as a decorator, or with args to return a decorator"""

    if callable(param):
        _hook_warn()
        return _OnStopDecorator(kwargs=kwargs)(param)

    return _OnStopDecorator(kwargs=kwargs)


@dataclass
class _CapDecorator(_HookDecorator[HookKwargs], ABC):
    caps: tuple[str, ...]


@dataclass
class _CapAvailableDecorator(_CapDecorator):
    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        hook = CapAvailableFuncHook.get_or_add_hook(func)
        hook.add_hook(self.caps, self.kwargs)
        return func


def on_cap_available(
    *caps: str, **kwargs: Unpack[HookKwargs]
) -> _CapAvailableDecorator:
    """External on_cap_available decorator. Must be used as a function that returns a decorator

    This hook will fire for each capability in a `CAP LS` response from the server
    """

    return _CapAvailableDecorator(caps=caps, kwargs=kwargs)


@dataclass
class _CapAckDecorator(_CapDecorator):
    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        hook = CapAckFuncHook.get_or_add_hook(func)
        hook.add_hook(self.caps, self.kwargs)
        return func


def on_cap_ack(*caps: str, **kwargs: Unpack[HookKwargs]) -> _CapAckDecorator:
    """External on_cap_ack decorator. Must be used as a function that returns a decorator

    This hook will fire for each capability that is acknowledged from the server with `CAP ACK`
    """

    return _CapAckDecorator(caps=caps, kwargs=kwargs)


@dataclass
class _ConnectDecorator(_HookDecorator[HookKwargs]):
    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        hook = ConnectFuncHook.get_or_add_hook(func)
        hook._add_hook(self.kwargs)
        return func


@overload
def on_connect(**kwargs: Unpack[HookKwargs]) -> _ConnectDecorator: ...


@overload
@deprecated(
    "Bare decorators are deprecated, use @on_connect() instead of @on_connect",
    category=DeprecationWarning,
)
def on_connect(param: Callable[_P, _T], /) -> Callable[_P, _T]: ...


def on_connect(
    param: Callable[_P, _T] | None = None, /, **kwargs: Unpack[HookKwargs]
) -> Callable[_P, _T] | _ConnectDecorator:
    if callable(param):
        _hook_warn()
        return _ConnectDecorator(kwargs)(param)

    return _ConnectDecorator(kwargs)


class _IrcOutDecorator(_HookDecorator[HookKwargs]):
    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        hook = IrcOutFuncHook.get_or_add_hook(func)
        hook._add_hook(self.kwargs)
        return func


@overload
def irc_out(**kwargs: Unpack[HookKwargs]) -> _IrcOutDecorator: ...


@overload
@deprecated(
    "Bare decorators are deprecated, use @irc_out() instead of @irc_out",
    category=DeprecationWarning,
)
def irc_out(param: Callable[_P, _T], /) -> Callable[_P, _T]: ...


def irc_out(
    param: Callable[_P, _T] | None = None, /, **kwargs: Unpack[HookKwargs]
) -> Callable[_P, _T] | _IrcOutDecorator:
    if callable(param):
        _hook_warn()
        return _IrcOutDecorator(kwargs=kwargs)(param)

    return _IrcOutDecorator(kwargs=kwargs)


@dataclass
class _PostHookDecorator(_HookDecorator[HookKwargs]):
    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        hook = PostHookFuncHook.get_or_add_hook(func)
        hook._add_hook(self.kwargs)
        return func


@overload
def post_hook(**kwargs: Unpack[HookKwargs]) -> _PostHookDecorator: ...


@overload
@deprecated(
    "Bare decorators are deprecated, use @post_hook() instead of @post_hook",
    category=DeprecationWarning,
)
def post_hook(param: Callable[_P, _T], /) -> Callable[_P, _T]: ...


def post_hook(
    param: Callable[_P, _T] | None = None, /, **kwargs: Unpack[HookKwargs]
) -> Callable[_P, _T] | _PostHookDecorator:
    """
    This hook will be fired just after a hook finishes executing
    """

    if callable(param):
        _hook_warn()
        return _PostHookDecorator(kwargs=kwargs)(param)

    return _PostHookDecorator(kwargs=kwargs)


@dataclass
class _PermissionDecorator(_HookDecorator[HookKwargs]):
    perms: tuple[str, ...]

    @override
    def __call__(self, func: Callable[_P, _T], /) -> Callable[_P, _T]:
        hook = PermissionFuncHook.get_or_add_hook(func)
        hook.add_hook(self.perms, self.kwargs)
        return func


def permission(
    *perms: str, **kwargs: Unpack[HookKwargs]
) -> _PermissionDecorator:
    return _PermissionDecorator(kwargs=kwargs, perms=perms)


_deprecated_aliases = {
    "_Hook": "FuncHook",
    "_CommandHook": "CommandFuncHook",
    "_RegexHook": "RegexFuncHook",
    "_RawHook": "RawFuncHook",
    "_PeriodicHook": "PeriodicFuncHook",
    "_EventHook": "EventFuncHook",
    "_CapHook": "CapFuncHook",
    "_PermissionHook": "PermissionFuncHook",
    "connect": "on_connect",
    "on_unload": "on_stop",
    "onload": "on_start",
}


def __getattr__(name: str) -> Any:  # pyright: ignore[reportAny]
    if name in _deprecated_aliases:
        new_name = _deprecated_aliases[name]
        warnings.warn(
            f"{name} is deprecated, use {new_name} instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[new_name]  # pyright: ignore[reportAny]

    raise AttributeError(name)
