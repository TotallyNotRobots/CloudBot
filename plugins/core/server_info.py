"""
Tracks verious server info like ISUPPORT tokens
"""
from collections import namedtuple

from cloudbot import hook

Status = namedtuple('Status', 'prefix mode level')
ChanMode = namedtuple('ChanMode', 'char type')

DEFAULT_STATUS = (
    Status('@', 'o', 2),
    Status('+', 'v', 1),
)


@hook.on_start
def do_isupport(bot):
    for conn in bot.connections.values():
        if conn.connected:
            clear_isupport(conn)
            conn.send("VERSION")


@hook.connect
def clear_isupport(conn):
    serv_info = conn.memory.setdefault("server_info", {})
    statuses = {s.prefix: s for s in DEFAULT_STATUS}
    statuses.update({s.mode: s for s in DEFAULT_STATUS})
    serv_info["statuses"] = statuses

    isupport_data = serv_info.setdefault("isupport_tokens", {})
    isupport_data.clear()


def handle_prefixes(data, serv_info):
    modes, prefixes = data.split(')', 1)
    modes = modes.strip('(')
    statuses = enumerate(reversed(list(zip(modes, prefixes))))
    parsed = {}
    for lvl, (mode, prefix) in statuses:
        status = Status(prefix, mode, lvl + 1)
        parsed[status.prefix] = status
        parsed[status.mode] = status

    serv_info["statuses"] = parsed


def handle_chan_modes(value, serv_info):
    types = "ABCD"
    modelist = serv_info.setdefault('channel_modes', {})
    modelist.clear()
    for i, modes in enumerate(value.split(',')):
        if i >= len(types):
            break

        for mode in modes:
            modelist[mode] = ChanMode(mode, types[i])


def handle_extbans(value, serv_info):
    pfx, extbans = value.split(',', 1)
    serv_info["extbans"] = extbans
    serv_info["extban_prefix"] = pfx


@hook.irc_raw('005', singlethread=True)
def on_isupport(conn, irc_paramlist):
    serv_info = conn.memory["server_info"]
    token_data = serv_info["isupport_tokens"]
    tokens = irc_paramlist[1:-1]  # strip the nick and trailing ':are supported by this server' message
    for token in tokens:
        name, _, value = token.partition('=')
        name = name.upper()
        token_data[name] = value or None
        if name == "PREFIX":
            handle_prefixes(value, serv_info)
        elif name == "CHANMODES":
            handle_chan_modes(value, serv_info)
        elif name == "EXTBAN":
            handle_extbans(value, serv_info)
