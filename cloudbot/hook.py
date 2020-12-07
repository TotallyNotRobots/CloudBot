import collections
import inspect
import re
from enum import Enum, IntEnum, unique

from cloudbot.event import EventType
from cloudbot.util import HOOK_ATTR

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

    HALTTYPE = (
        0  # Once this hook executes, no other hook of that type should run
    )
    HALTALL = 1  # Once this hook executes, No other hook should run
    CONTINUE = 2  # Normal execution of all hooks


class _Hook:
    """
    :type function: function
    :type type: str
    :type kwargs: dict[str, unknown]
    """

    def __init__(self, function, _type):
        """
        :type function: function
        :type _type: str
        """
        self.function = function
        self.type = _type
        self.kwargs = {}

    def _add_hook(self, kwargs):
        """
        :type kwargs: dict[str, unknown]
        """
        # update kwargs, overwriting duplicates
        self.kwargs.update(kwargs)


class _CommandHook(_Hook):
    """
    :type main_alias: str
    :type aliases: set[str]
    """

    def __init__(self, function):
        """
        :type function: function
        """
        _Hook.__init__(self, function, "command")
        self.aliases = set()
        self.main_alias = None

        if function.__doc__:
            doc = inspect.cleandoc(function.__doc__)
            # Split on the first entirely blank line
            self.doc = " ".join(
                doc.split("\n\n", 1)[0].strip("\n").split("\n")
            ).strip()
        else:
            self.doc = None

    def add_hook(self, alias_param, kwargs):
        """
        :type alias_param: list[str] | str
        """
        self._add_hook(kwargs)

        if not alias_param:
            alias_param = self.function.__name__
        if isinstance(alias_param, str):
            alias_param = [alias_param]
        if not self.main_alias:
            self.main_alias = alias_param[0]
        for alias in alias_param:
            if not valid_command_re.match(alias):
                raise ValueError("Invalid command name {}".format(alias))
        self.aliases.update(alias_param)


class _RegexHook(_Hook):
    """
    :type regexes: list[re.__Regex]
    """

    def __init__(self, function):
        """
        :type function: function
        """
        _Hook.__init__(self, function, "regex")
        self.regexes = []

    def add_hook(self, regex_param, kwargs):
        """
        :type regex_param: Iterable[str | re.__Regex] | str | re.__Regex
        :type kwargs: dict[str, unknown]
        """
        self._add_hook(kwargs)
        # add all regex_parameters to valid regexes
        if isinstance(regex_param, str):
            # if the parameter is a string, compile and add
            self.regexes.append(re.compile(regex_param))
        elif hasattr(regex_param, "search"):
            # if the parameter is an re.__Regex, just add it
            # we only use regex.search anyways, so this is a good determiner
            self.regexes.append(regex_param)
        else:
            assert isinstance(regex_param, collections.abc.Iterable)
            # if the parameter is a list, add each one
            for re_to_match in regex_param:
                if isinstance(re_to_match, str):
                    re_to_match = re.compile(re_to_match)
                else:
                    # make sure that the param is either a compiled regex, or has a search attribute.
                    assert hasattr(re_to_match, "search")
                self.regexes.append(re_to_match)


class _RawHook(_Hook):
    """
    :type triggers: set[str]
    """

    def __init__(self, function):
        """
        :type function: function
        """
        _Hook.__init__(self, function, "irc_raw")
        self.triggers = set()

    def add_hook(self, trigger_param, kwargs):
        """
        :type trigger_param: list[str] | str
        :type kwargs: dict[str, unknown]
        """
        self._add_hook(kwargs)

        if isinstance(trigger_param, str):
            self.triggers.add(trigger_param)
        else:
            # it's a list
            self.triggers.update(trigger_param)


class _PeriodicHook(_Hook):
    def __init__(self, function):
        """
        :type function: function
        """
        _Hook.__init__(self, function, "periodic")
        self.interval = 60.0

    def add_hook(self, interval, kwargs):
        """
        :type interval: int
        :type kwargs: dict[str, unknown]
        """
        self._add_hook(kwargs)

        if interval:
            self.interval = interval


class _EventHook(_Hook):
    """
    :type types: set[cloudbot.event.EventType]
    """

    def __init__(self, function):
        """
        :type function: function
        """
        _Hook.__init__(self, function, "event")
        self.types = set()

    def add_hook(self, trigger_param, kwargs):
        """
        :type trigger_param: cloudbot.event.EventType | list[cloudbot.event.EventType]
        :type kwargs: dict[str, unknown]
        """
        self._add_hook(kwargs)

        if isinstance(trigger_param, EventType):
            self.types.add(trigger_param)
        else:
            # it's a list
            self.types.update(trigger_param)


class _CapHook(_Hook):
    def __init__(self, func, _type):
        super().__init__(func, "on_cap_{}".format(_type))
        self.caps = set()

    def add_hook(self, caps, kwargs):
        self._add_hook(kwargs)
        self.caps.update(caps)


class _PermissionHook(_Hook):
    def __init__(self, func):
        super().__init__(func, "perm_check")
        self.perms = set()

    def add_hook(self, perms, kwargs):
        self._add_hook(kwargs)
        self.perms.update(perms)


def _add_hook(func, hook):
    if not hasattr(func, HOOK_ATTR):
        setattr(func, HOOK_ATTR, {})
    else:
        # in this case the hook should be using the add_hook method
        assert hook.type not in getattr(func, HOOK_ATTR)

    getattr(func, HOOK_ATTR)[hook.type] = hook


def _get_hook(func, hook_type):
    if hasattr(func, HOOK_ATTR) and hook_type in getattr(func, HOOK_ATTR):
        return getattr(func, HOOK_ATTR)[hook_type]

    return None


def command(*args, **kwargs):
    """External command decorator. Can be used directly as a decorator, or with args to return a decorator.
    :type param: str | list[str] | function
    """

    def _command_hook(func, alias_param=None):
        hook = _get_hook(func, "command")
        if hook is None:
            hook = _CommandHook(func)
            _add_hook(func, hook)

        hook.add_hook(alias_param, kwargs)
        return func

    if len(args) == 1 and callable(
        args[0]
    ):  # this decorator is being used directly
        return _command_hook(args[0])

    # this decorator is being used indirectly, so return a decorator function
    return lambda func: _command_hook(func, alias_param=args)


def irc_raw(triggers_param, **kwargs):
    """External raw decorator. Must be used as a function to return a decorator
    :type triggers_param: str | list[str]
    """

    def _raw_hook(func):
        hook = _get_hook(func, "irc_raw")
        if hook is None:
            hook = _RawHook(func)
            _add_hook(func, hook)

        hook.add_hook(triggers_param, kwargs)
        return func

    if callable(
        triggers_param
    ):  # this decorator is being used directly, which isn't good
        raise TypeError(
            "@irc_raw() must be used as a function that returns a decorator"
        )

    # this decorator is being used as a function, so return a decorator
    return _raw_hook


def event(types_param, **kwargs):
    """External event decorator. Must be used as a function to return a decorator
    :type types_param: cloudbot.event.EventType | list[cloudbot.event.EventType]
    """

    def _event_hook(func):
        hook = _get_hook(func, "event")
        if hook is None:
            hook = _EventHook(func)
            _add_hook(func, hook)

        hook.add_hook(types_param, kwargs)
        return func

    if callable(
        types_param
    ):  # this decorator is being used directly, which isn't good
        raise TypeError(
            "@irc_raw() must be used as a function that returns a decorator"
        )

    # this decorator is being used as a function, so return a decorator
    return _event_hook


def regex(regex_param, **kwargs):
    """External regex decorator. Must be used as a function to return a decorator.
    :type regex_param: str | re.__Regex | list[str | re.__Regex]
    :type flags: int
    """

    def _regex_hook(func):
        hook = _get_hook(func, "regex")
        if hook is None:
            hook = _RegexHook(func)
            _add_hook(func, hook)

        hook.add_hook(regex_param, kwargs)
        return func

    if callable(
        regex_param
    ):  # this decorator is being used directly, which isn't good
        raise TypeError(
            "@regex() hook must be used as a function that returns a decorator"
        )

    # this decorator is being used as a function, so return a decorator
    return _regex_hook


def sieve(param=None, **kwargs):
    """External sieve decorator. Can be used directly as a decorator, or with args to return a decorator
    :type param: function | None
    """

    def _sieve_hook(func):
        assert (
            len(inspect.signature(func).parameters) == 3
        ), "Sieve plugin has incorrect argument count. Needs params: bot, input, plugin"

        hook = _get_hook(func, "sieve")
        if hook is None:
            hook = _Hook(
                func, "sieve"
            )  # there's no need to have a specific SieveHook object
            _add_hook(func, hook)

        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _sieve_hook(param)

    return _sieve_hook


def periodic(interval, **kwargs):
    """External on_start decorator. Can be used directly as a decorator, or with args to return a decorator
    :type param: function | None
    """

    def _periodic_hook(func):
        hook = _get_hook(func, "periodic")
        if hook is None:
            hook = _PeriodicHook(func)
            _add_hook(func, hook)

        hook.add_hook(interval, kwargs)
        return func

    if callable(
        interval
    ):  # this decorator is being used directly, which isn't good
        raise TypeError(
            "@periodic() hook must be used as a function that returns a decorator"
        )

    # this decorator is being used as a function, so return a decorator
    return _periodic_hook


def config(param=None, **kwargs):
    """
    External on_start decorator. Can be used directly as a decorator,
    or with args to return a decorator.

    :type param: function | None
    """

    def _config_hook(func):
        hook = _get_hook(func, "config")
        if hook is None:
            hook = _Hook(func, "config")
            _add_hook(func, hook)

        hook._add_hook(kwargs)
        return func

    return _config_hook


def on_start(param=None, **kwargs):
    """External on_start decorator. Can be used directly as a decorator, or with args to return a decorator
    :type param: function | None
    """

    def _on_start_hook(func):
        hook = _get_hook(func, "on_start")
        if hook is None:
            hook = _Hook(func, "on_start")
            _add_hook(func, hook)

        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _on_start_hook(param)

    return _on_start_hook


# this is temporary, to ease transition
onload = on_start


def on_stop(param=None, **kwargs):
    """External on_stop decorator. Can be used directly as a decorator, or with args to return a decorator
    :type param: function | None
    """

    def _on_stop_hook(func):
        hook = _get_hook(func, "on_stop")
        if hook is None:
            hook = _Hook(func, "on_stop")
            _add_hook(func, hook)
        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _on_stop_hook(param)

    return _on_stop_hook


on_unload = on_stop


def on_cap_available(*caps, **kwargs):
    """External on_cap_available decorator. Must be used as a function that returns a decorator

    This hook will fire for each capability in a `CAP LS` response from the server
    """

    def _on_cap_available_hook(func):
        hook = _get_hook(func, "on_cap_available")
        if hook is None:
            hook = _CapHook(func, "available")
            _add_hook(func, hook)
        hook.add_hook(caps, kwargs)
        return func

    return _on_cap_available_hook


def on_cap_ack(*caps, **kwargs):
    """External on_cap_ack decorator. Must be used as a function that returns a decorator

    This hook will fire for each capability that is acknowledged from the server with `CAP ACK`
    """

    def _on_cap_ack_hook(func):
        hook = _get_hook(func, "on_cap_ack")
        if hook is None:
            hook = _CapHook(func, "ack")
            _add_hook(func, hook)
        hook.add_hook(caps, kwargs)
        return func

    return _on_cap_ack_hook


def on_connect(param=None, **kwargs):
    def _on_connect_hook(func):
        hook = _get_hook(func, "on_connect")
        if hook is None:
            hook = _Hook(func, "on_connect")
            _add_hook(func, hook)
        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _on_connect_hook(param)

    return _on_connect_hook


connect = on_connect


def irc_out(param=None, **kwargs):
    def _decorate(func):
        hook = _get_hook(func, "irc_out")
        if hook is None:
            hook = _Hook(func, "irc_out")
            _add_hook(func, hook)

        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _decorate(param)

    return _decorate


def post_hook(param=None, **kwargs):
    """
    This hook will be fired just after a hook finishes executing
    """

    def _decorate(func):
        hook = _get_hook(func, "post_hook")
        if hook is None:
            hook = _Hook(func, "post_hook")
            _add_hook(func, hook)

        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _decorate(param)

    return _decorate


def permission(*perms, **kwargs):
    def _perm_hook(func):
        hook = _get_hook(func, "perm_check")
        if hook is None:
            hook = _PermissionHook(func)
            _add_hook(func, hook)

        hook.add_hook(perms, kwargs)
        return func

    return _perm_hook
