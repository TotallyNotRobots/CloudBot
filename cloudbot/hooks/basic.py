import re
from abc import abstractmethod, ABC

from ..event import EventType
from ..hooks.types import HookTypes
from ..util.abc import Iterable
from ..util.text import is_command


class BaseHook(ABC):
    """
    :type function: function
    :type kwargs: dict[str, unknown]
    """

    def __init__(self, func):
        """
        :type func: function
        """
        self.function = func
        self.kwargs = {}

        self._setup()

    def _setup(self):
        pass

    def _add_hook(self, kwargs):
        """
        :type kwargs: dict[str, unknown]
        """
        # update kwargs, overwriting duplicates
        self.kwargs.update(kwargs)

    @classmethod
    @abstractmethod
    def get_type(cls):
        raise NotImplementedError

    @classmethod
    def get_type_name(cls):
        return cls.get_type().type

    @property
    def type(self):
        return self.get_type().type

    def make_full_hook(self, plugin):
        return self.get_type().full_hook(plugin, self)


class BaseCommandHook(BaseHook):
    main_alias = None

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
        :type kwargs: dict[str, Any]
        """
        self._add_hook(kwargs)

        if not alias_param:
            alias_param = self.function.__name__

        if isinstance(alias_param, str):
            alias_param = [alias_param]

        if not self.main_alias:
            self.main_alias = alias_param[0]

        for alias in alias_param:
            if not is_command(alias):
                raise ValueError("Invalid command name {}".format(alias))

        self.aliases.update(alias_param)


class BaseRegexHook(BaseHook):
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
            assert isinstance(regex_param, Iterable)
            # if the parameter is a list, add each one
            for re_to_match in regex_param:
                if isinstance(re_to_match, str):
                    re_to_match = re.compile(re_to_match)
                else:
                    # make sure that the param is either a compiled regex, or has a search attribute.
                    assert hasattr(re_to_match, "search")
                self.regexes.append(re_to_match)


class BaseRawHook(BaseHook):
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


class BasePeriodicHook(BaseHook):
    interval = None

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


class BaseEventHook(BaseHook):
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


class BaseCapHook(BaseHook):
    @classmethod
    @abstractmethod
    def get_type(cls):
        raise NotImplementedError

    def _setup(self):
        self.caps = set()

    def add_hook(self, caps, kwargs):
        self._add_hook(kwargs)
        self.caps.update(caps)


class BaseCapAvailableHook(BaseCapHook):
    @classmethod
    def get_type(cls):
        return HookTypes.CAPAVAILABLE


class BaseCapAckHook(BaseCapHook):
    @classmethod
    def get_type(cls):
        return HookTypes.CAPACK


class BasePermissionHook(BaseHook):
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

        def add_hook(self, kwargs):
            self._add_hook(kwargs)

    return _BasicHook


BaseSieveHook = _basic_hook(HookTypes.SIEVE)
BaseOnStartHook = _basic_hook(HookTypes.ONSTART)
BaseOnStopHook = _basic_hook(HookTypes.ONSTOP)
BaseOnConnectHook = _basic_hook(HookTypes.CONNECT)
BasePostHookHook = _basic_hook(HookTypes.POSTHOOK)
BaseIrcOutHook = _basic_hook(HookTypes.IRCOUT)
