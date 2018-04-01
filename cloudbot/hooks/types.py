import enum
from collections import namedtuple
from enum import Enum

from .full import *

HookType = namedtuple('HookType', 'type full_hook')


@enum.unique
class HookTypes(HookType, Enum):
    COMMAND = HookType('command', CommandHook)
    EVENT = HookType('event', EventHook)
    REGEX = HookType('regex', RegexHook)
    PERIODIC = HookType('periodic', PeriodicHook)
    ONSTART = HookType('on_start', OnStartHook)
    ONSTOP = HookType('on_stop', OnStopHook)
    CONNECT = HookType('on_connect', OnConnectHook)
    PERMISSION = HookType('perm_check', PermHook)
    SIEVE = HookType('sieve', SieveHook)
    POSTHOOK = HookType('post_hook', PostHookHook)

    IRCRAW = HookType('irc_raw', RawHook)
    IRCOUT = HookType('irc_out', IrcOutHook)
    CAPACK = HookType('on_cap_ack', OnCapAckHook)
    CAPAVAILABLE = HookType('on_cap_available', OnCapAvaliableHook)
