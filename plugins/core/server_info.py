"""
Tracks verious server info like ISUPPORT tokens
"""
from typing import Callable, Dict, MutableMapping, TypeVar

from cloudbot import hook
from cloudbot.util.irc import ChannelMode, ModeType, StatusMode

DEFAULT_STATUS = (
    StatusMode.make("@", "o", 2),
    StatusMode.make("+", "v", 1),
)


@hook.on_start()
def do_isupport(bot):
    for conn in bot.connections.values():
        if conn.connected:
            clear_isupport(conn)
            conn.send("VERSION")


@hook.connect()
def clear_isupport(conn):
    serv_info = conn.memory.setdefault("server_info", {})
    statuses = get_status_modes(serv_info, clear=True)
    for s in DEFAULT_STATUS:
        statuses[s.prefix] = s
        statuses[s.character] = s

    get_channel_modes(serv_info, clear=True)

    isupport_data = serv_info.setdefault("isupport_tokens", {})
    isupport_data.clear()


K = TypeVar("K")
V = TypeVar("V", bound=MutableMapping)


def _get_set_clear(
    mapping: MutableMapping[K, V],
    key: K,
    default_factory: Callable[[], V],
    *,
    clear: bool = False,
) -> V:
    try:
        out = mapping[key]
    except KeyError:
        mapping[key] = out = default_factory()

    if clear:
        out.clear()

    return out


def get_server_info(conn):
    return conn.memory["server_info"]


def get_status_modes(
    serv_info, *, clear: bool = False
) -> Dict[str, StatusMode]:
    return _get_set_clear(serv_info, "statuses", dict, clear=clear)


def get_channel_modes(
    serv_info, *, clear: bool = False
) -> Dict[str, ChannelMode]:
    return _get_set_clear(serv_info, "channel_modes", dict, clear=clear)


def sync_statuses(serv_info):
    """
    Copy channel status modes to the modelist
    """
    statuses = get_status_modes(serv_info)
    modes = get_channel_modes(serv_info)

    for status in statuses.values():
        modes[status.character] = status


def handle_prefixes(data, serv_info):
    modes, prefixes = data.split(")", 1)
    modes = modes.strip("(")
    parsed = enumerate(reversed(list(zip(modes, prefixes))))
    statuses = get_status_modes(serv_info, clear=True)
    for lvl, (mode, prefix) in parsed:
        status = StatusMode.make(prefix, mode, lvl + 1)
        statuses[status.prefix] = status
        statuses[status.character] = status

    sync_statuses(serv_info)


def handle_chan_modes(value, serv_info):
    types = "ABCD"
    modelist = get_channel_modes(serv_info, clear=True)
    for i, modes in enumerate(value.split(",")):
        if i >= len(types):
            break

        for mode in modes:
            modelist[mode] = ChannelMode(mode, ModeType(types[i]))

    sync_statuses(serv_info)


def handle_extbans(value, serv_info):
    pfx, extbans = value.split(",", 1)
    serv_info["extbans"] = extbans
    serv_info["extban_prefix"] = pfx


isupport_handlers = {
    "PREFIX": handle_prefixes,
    "CHANMODES": handle_chan_modes,
    "EXTBAN": handle_extbans,
}


@hook.irc_raw("005", singlethread=True)
def on_isupport(conn, irc_paramlist):
    serv_info = get_server_info(conn)
    token_data = serv_info["isupport_tokens"]
    # strip the nick and trailing ':are supported by this server' message
    tokens = irc_paramlist[1:-1]
    for token in tokens:
        name, _, value = token.partition("=")
        name = name.upper()
        token_data[name] = value or None
        handler = isupport_handlers.get(name)
        if handler:
            handler(value, serv_info)
