import collections
import re
from abc import abstractmethod

from cloudbot.event import EventType
from cloudbot.hooks.basic import BaseHook
from cloudbot.hooks.types import HookTypes

valid_command_re = re.compile(r"^\w+$")


from .hooks.actions import Action
from .hooks.priority import Priority


_HOOK_DATA_FIELD = '_cloudbot_hook'


class _CommandHook(BaseHook):
    @classmethod
    def get_type(cls):
        return HookTypes.COMMAND

    def _setup(self):
        self.aliases = set()
        self.main_alias = None

        if self.function.__doc__:
            self.doc = self.function.__doc__.split('\n', 1)[0]
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


class _RegexHook(BaseHook):
    @classmethod
    def get_type(cls):
        return HookTypes.REGEX

    def _setup(self):
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
            assert isinstance(regex_param, collections.Iterable)
            # if the parameter is a list, add each one
            for re_to_match in regex_param:
                if isinstance(re_to_match, str):
                    re_to_match = re.compile(re_to_match)
                else:
                    # make sure that the param is either a compiled regex, or has a search attribute.
                    assert hasattr(re_to_match, "search")
                self.regexes.append(re_to_match)


class _RawHook(BaseHook):
    @classmethod
    def get_type(cls):
        return HookTypes.IRCRAW

    def _setup(self):
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


class _PeriodicHook(BaseHook):
    @classmethod
    def get_type(cls):
        return HookTypes.PERIODIC

    def _setup(self):
        self.interval = 60.0

    def add_hook(self, interval, kwargs):
        """
        :type interval: int
        :type kwargs: dict[str, unknown]
        """
        self._add_hook(kwargs)

        if interval:
            self.interval = interval


class _EventHook(BaseHook):
    @classmethod
    def get_type(cls):
        return HookTypes.EVENT

    def _setup(self):
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


class _CapHook(BaseHook):
    @classmethod
    @abstractmethod
    def get_type(cls):
        raise NotImplementedError

    def _setup(self):
        self.caps = set()

    def add_hook(self, caps, kwargs):
        self._add_hook(kwargs)
        self.caps.update(caps)


class _CapAvailableHook(_CapHook):
    @classmethod
    def get_type(cls):
        return HookTypes.CAPAVAILABLE


class _CapAckHook(_CapHook):
    @classmethod
    def get_type(cls):
        return HookTypes.CAPACK


class _PermissionHook(BaseHook):
    @classmethod
    def get_type(cls):
        return HookTypes.PERMISSION

    def _setup(self):
        self.perms = set()

    def add_hook(self, perms, kwargs):
        self._add_hook(kwargs)
        self.perms.update(perms)


def _basic_hook(hook_type):
    class _BasicHook(BaseHook):
        @classmethod
        def get_type(cls):
            return hook_type

    return _BasicHook


_SieveHook = _basic_hook(HookTypes.SIEVE)
_OnStartHook = _basic_hook(HookTypes.ONSTART)
_OnStopHook = _basic_hook(HookTypes.ONSTOP)
_OnConnectHook = _basic_hook(HookTypes.CONNECT)
_PostHookHook = _basic_hook(HookTypes.POSTHOOK)
_IrcOutHook = _basic_hook(HookTypes.IRCOUT)


def get_hooks(func):
    return getattr(func, _HOOK_DATA_FIELD)


def _add_hook(func, hook):
    try:
        hooks = get_hooks(func)
    except AttributeError:
        hooks = {}
        setattr(func, _HOOK_DATA_FIELD, hooks)
    else:
        if hook.type in hooks:
            raise TypeError("Attempted to add a duplicate hook")

    hooks[hook.type] = hook


def _get_hook(func, hook_type):
    try:
        hooks = get_hooks(func)
    except AttributeError:
        return None

    return hooks.get(hook_type)


def _get_or_add_hook(func, hook_cls):
    hook = _get_hook(func, hook_cls.get_type())
    if hook is None:
        hook = hook_cls(func)
        _add_hook(func, hook)

    return hook


def command(*args, **kwargs):
    def _command_hook(func, alias_param=None):
        hook = _get_or_add_hook(func, _CommandHook)

        hook.add_hook(alias_param, kwargs)
        return func

    if len(args) == 1 and callable(args[0]):  # this decorator is being used directly
        return _command_hook(args[0])
    else:  # this decorator is being used indirectly, so return a decorator function
        return lambda func: _command_hook(func, alias_param=args)


def irc_raw(triggers_param, **kwargs):
    """External raw decorator. Must be used as a function to return a decorator
    :type triggers_param: str | list[str]
    """

    kwargs['clients'] = 'irc'

    def _raw_hook(func):
        hook = _get_or_add_hook(func, _RawHook)
        hook.add_hook(triggers_param, kwargs)
        return func

    if callable(triggers_param):  # this decorator is being used directly, which isn't good
        raise TypeError("@irc_raw() must be used as a function that returns a decorator")
    else:  # this decorator is being used as a function, so return a decorator
        return lambda func: _raw_hook(func)


def event(types_param, **kwargs):
    """External event decorator. Must be used as a function to return a decorator
    :type types_param: cloudbot.event.EventType | list[cloudbot.event.EventType]
    """

    def _event_hook(func):
        hook = _get_or_add_hook(func, _EventHook)

        hook.add_hook(types_param, kwargs)
        return func

    if callable(types_param):  # this decorator is being used directly, which isn't good
        raise TypeError("@irc_raw() must be used as a function that returns a decorator")
    else:  # this decorator is being used as a function, so return a decorator
        return lambda func: _event_hook(func)


def regex(regex_param, **kwargs):
    """External regex decorator. Must be used as a function to return a decorator.
    :type regex_param: str | re.__Regex | list[str | re.__Regex]
    :type flags: int
    """

    def _regex_hook(func):
        hook = _get_or_add_hook(func, _RegexHook)

        hook.add_hook(regex_param, kwargs)
        return func

    if callable(regex_param):  # this decorator is being used directly, which isn't good
        raise TypeError("@regex() hook must be used as a function that returns a decorator")
    else:  # this decorator is being used as a function, so return a decorator
        return lambda func: _regex_hook(func)


def sieve(param=None, **kwargs):
    """External sieve decorator. Can be used directly as a decorator, or with args to return a decorator
    :type param: function | None
    """

    def _sieve_hook(func):
        hook = _get_or_add_hook(func, _SieveHook)

        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _sieve_hook(param)
    else:
        return lambda func: _sieve_hook(func)


def periodic(interval, **kwargs):
    """External on_start decorator. Can be used directly as a decorator, or with args to return a decorator
    :type param: function | None
    """

    def _periodic_hook(func):
        hook = _get_or_add_hook(func, _PeriodicHook)

        hook.add_hook(interval, kwargs)
        return func

    if callable(interval):  # this decorator is being used directly, which isn't good
        raise TypeError("@periodic() hook must be used as a function that returns a decorator")
    else:  # this decorator is being used as a function, so return a decorator
        return lambda func: _periodic_hook(func)


def on_start(param=None, **kwargs):
    """External on_start decorator. Can be used directly as a decorator, or with args to return a decorator
    :type param: function | None
    """

    def _on_start_hook(func):
        hook = _get_or_add_hook(func, _OnStartHook)

        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _on_start_hook(param)
    else:
        return lambda func: _on_start_hook(func)


# this is temporary, to ease transition
onload = on_start


def on_stop(param=None, **kwargs):
    """External on_stop decorator. Can be used directly as a decorator, or with args to return a decorator
    :type param: function | None
    """

    def _on_stop_hook(func):
        hook = _get_or_add_hook(func, _OnStopHook)

        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _on_stop_hook(param)
    else:
        return lambda func: _on_stop_hook(func)


on_unload = on_stop


def on_cap_available(*caps, **kwargs):
    """External on_cap_available decorator. Must be used as a function that returns a decorator

    This hook will fire for each capability in a `CAP LS` response from the server
    """

    kwargs['clients'] = 'irc'

    def _on_cap_available_hook(func):
        hook = _get_or_add_hook(func, _CapAvailableHook)
        hook.add_hook(caps, kwargs)
        return func

    return _on_cap_available_hook


def on_cap_ack(*caps, **kwargs):
    """External on_cap_ack decorator. Must be used as a function that returns a decorator

    This hook will fire for each capability that is acknowledged from the server with `CAP ACK`
    """

    kwargs['clients'] = 'irc'

    def _on_cap_ack_hook(func):
        hook = _get_or_add_hook(func, _CapAckHook)
        hook.add_hook(caps, kwargs)
        return func

    return _on_cap_ack_hook


def on_connect(param=None, **kwargs):
    def _on_connect_hook(func):
        hook = _get_or_add_hook(func, _OnConnectHook)
        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _on_connect_hook(param)
    else:
        return lambda func: _on_connect_hook(func)


connect = on_connect


def irc_out(param=None, **kwargs):
    kwargs['clients'] = 'irc'

    def _decorate(func):
        hook = _get_or_add_hook(func, _IrcOutHook)

        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _decorate(param)
    else:
        return lambda func: _decorate(func)


def post_hook(param=None, **kwargs):
    """
    This hook will be fired just after a hook finishes executing
    """

    def _decorate(func):
        hook = _get_or_add_hook(func, _PostHookHook)

        hook._add_hook(kwargs)
        return func

    if callable(param):
        return _decorate(param)
    else:
        return lambda func: _decorate(func)


def permission(*perms, **kwargs):
    def _perm_hook(func):
        hook = _get_or_add_hook(func, _PermissionHook)

        hook.add_hook(perms, kwargs)
        return func

    return lambda func: _perm_hook(func)
