from .hooks.basic import *

_HOOK_DATA_FIELD = '_cloudbot_hook'


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
            raise TypeError("Attempted to add a duplicate hook", func, hook, hook.type)

    hooks[hook.type] = hook


def _get_hook(func, hook_type):
    try:
        hooks = get_hooks(func)
    except AttributeError:
        return None

    try:
        hook = hooks[hook_type]
    except KeyError:
        return None
    else:
        if hook is None:
            raise TypeError("Expected Hook, got None")

    return hook


def _get_or_add_hook(func, hook_cls):
    hook = _get_hook(func, hook_cls.get_type_name())
    if hook is None:
        hook = hook_cls(func)
        _add_hook(func, hook)

    return hook


def command(*args, **kwargs):
    def _command_hook(func, alias_param=None):
        hook = _get_or_add_hook(func, BaseCommandHook)

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
        hook = _get_or_add_hook(func, BaseRawHook)
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
        hook = _get_or_add_hook(func, BaseEventHook)

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
        hook = _get_or_add_hook(func, BaseRegexHook)

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
        hook = _get_or_add_hook(func, BaseSieveHook)

        hook.add_hook(kwargs)
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
        hook = _get_or_add_hook(func, BasePeriodicHook)

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
        hook = _get_or_add_hook(func, BaseOnStartHook)

        hook.add_hook(kwargs)
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
        hook = _get_or_add_hook(func, BaseOnStopHook)

        hook.add_hook(kwargs)
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
        hook = _get_or_add_hook(func, BaseCapAvailableHook)
        hook.add_hook(caps, kwargs)
        return func

    return _on_cap_available_hook


def on_cap_ack(*caps, **kwargs):
    """External on_cap_ack decorator. Must be used as a function that returns a decorator

    This hook will fire for each capability that is acknowledged from the server with `CAP ACK`
    """

    kwargs['clients'] = 'irc'

    def _on_cap_ack_hook(func):
        hook = _get_or_add_hook(func, BaseCapAckHook)
        hook.add_hook(caps, kwargs)
        return func

    return _on_cap_ack_hook


def on_connect(param=None, **kwargs):
    def _on_connect_hook(func):
        hook = _get_or_add_hook(func, BaseOnConnectHook)
        hook.add_hook(kwargs)
        return func

    if callable(param):
        return _on_connect_hook(param)
    else:
        return lambda func: _on_connect_hook(func)


connect = on_connect


def irc_out(param=None, **kwargs):
    kwargs['clients'] = 'irc'

    def _decorate(func):
        hook = _get_or_add_hook(func, BaseIrcOutHook)

        hook.add_hook(kwargs)
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
        hook = _get_or_add_hook(func, BasePostHookHook)

        hook.add_hook(kwargs)
        return func

    if callable(param):
        return _decorate(param)
    else:
        return lambda func: _decorate(func)


def permission(*perms, **kwargs):
    def _perm_hook(func):
        hook = _get_or_add_hook(func, BasePermissionHook)

        hook.add_hook(perms, kwargs)
        return func

    return lambda func: _perm_hook(func)
