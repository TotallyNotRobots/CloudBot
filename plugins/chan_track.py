"""
Track channel ops for permissions checks

Requires:
server_info.py
"""
import re
import weakref
from collections import defaultdict
from operator import attrgetter
from weakref import WeakValueDictionary

from cloudbot import hook

NUH_RE = re.compile(r'(?P<nick>.+?)(?:!(?P<user>.+?))?(?:@(?P<host>.+?))?')


class WeakDict(dict):
    # Subclass dict to allow it to be weakly referenced
    pass


class DataDict(defaultdict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __contains__(self, item):
        return super().__contains__(item.casefold())

    def __getitem__(self, item):
        return super().__getitem__(item.casefold())

    def __setitem__(self, key, value):
        super().__setitem__(key.casefold(), value)

    def __delitem__(self, key):
        super().__delitem__(key.casefold())

    def __missing__(self, key):
        data = WeakDict(name=key, users={})
        self[key] = data
        return data


def update_chan_data(conn, chan):
    chan_data = conn.memory["chan_data"][chan]
    chan_data["receiving_names"] = False
    conn.cmd("NAMES", chan)


def update_conn_data(conn):
    for chan in set(conn.channels):
        update_chan_data(conn, chan)


@hook.on_cap_available("userhost-in-names", "multi-prefix")
def do_caps():
    pass


@hook.on_start
def get_chan_data(bot):
    for conn in bot.connections.values():
        if conn.connected:
            update_conn_data(conn)


@hook.connect
def init_chan_data(conn):
    chan_data = conn.memory.setdefault("chan_data", DataDict())
    chan_data.clear()

    users = conn.memory.setdefault("users", WeakValueDictionary())
    users.clear()


def parse_nuh(mask):
    match = NUH_RE.fullmatch(mask)
    if not match:
        return None, None, None

    nick = match.group('nick')
    user = match.group('user')
    host = match.group('host')
    return nick, user, host


def replace_user_data(conn, chan_data):
    statuses = {status.prefix: status for status in set(conn.memory["server_info"]["statuses"].values())}
    users = conn.memory["users"]
    old_users = chan_data['users']
    new_data = chan_data.pop("new_users", [])
    new_users = {}
    caps = conn.memory.get("server_caps", {})
    has_uh_i_n = caps.get("userhost-in-names", False)
    has_multi_pfx = caps.get("multi-prefix", False)
    for name in new_data:
        user_data = WeakDict()
        memb_data = WeakDict(user=user_data, chan=weakref.proxy(chan_data))
        user_statuses = []
        while name[:1] in statuses:
            status, name = name[:1], name[1:]
            user_statuses.append(statuses[status])
            if not has_multi_pfx:
                # Only run once if we don't have multi-prefix enabled
                break

        user_statuses.sort(key=attrgetter("level"), reverse=True)
        # At this point, user_status[0] will the the Status object representing the highest status the user has
        # in the channel
        memb_data["status"] = user_statuses

        if has_uh_i_n:
            nick, user, host = parse_nuh(name)
            user_data.update({"nick": nick, "ident": user, "host": host})
        else:
            user_data["nick"] = name

        nick_cf = user_data["nick"].casefold()
        new_users[nick_cf] = memb_data
        if nick_cf in old_users:
            old_data = old_users[nick_cf]
            old_data.update(memb_data)  # New data takes priority over old data
            memb_data.update(old_data)

        old_user_data = users.setdefault(nick_cf, user_data)
        old_user_data.update(user_data)
        user_data = old_user_data
        memb_data["user"] = user_data
        user_chans = user_data.setdefault("channels", WeakValueDictionary())
        user_chans[chan_data["name"].casefold()] = memb_data

    old_users.clear()
    old_users.update(new_users)  # Reassigning the dict would break other references to the data, so just update instead


@hook.irc_raw(['353', '366'], singlethread=True)
def on_names(conn, irc_paramlist, irc_command):
    chan = irc_paramlist[2 if irc_command == '353' else 1]
    chan_data = conn.memory["chan_data"][chan]
    if irc_command == '366':
        chan_data["receiving_names"] = False
        replace_user_data(conn, chan_data)
        return

    users = chan_data.setdefault("new_users", [])
    if not chan_data.get("receiving_names"):
        chan_data["receiving_names"] = True
        users.clear()

    names = irc_paramlist[-1]
    if names.startswith(':'):
        names = names[1:].strip()

    users.extend(names.split())


def dump_dict(data, indent=2, level=0, _objects=None):
    if _objects is None:
        _objects = [id(data)]

    for key, value in data.items():
        yield ((" " * (indent * level)) + "{}:".format(key))
        if id(value) in _objects:
            yield ((" " * (indent * (level + 1))) + "[...]")
        elif isinstance(value, dict):
            _objects.append(id(value))
            yield from dump_dict(value, indent=indent, level=level + 1, _objects=_objects)
        else:
            _objects.append(id(value))
            yield ((" " * (indent * (level + 1))) + "{}".format(value))


@hook.permission("chanop")
def perm_check(chan, conn, nick):
    if not chan:
        return False

    chans = conn.memory["chan_data"]
    if chan not in chans:
        return False

    chan_data = chans[chan]
    nick_cf = nick.casefold()
    if nick_cf not in chan_data["users"]:
        return False

    memb = chan_data["users"][nick_cf]
    status = memb["status"]
    if status and status[0].level > 1:
        return True

    return False


@hook.command(permissions=["botcontrol"], autohelp=False)
def dumpchans(conn):
    """- Dumps all stored channel data for this connection to the console"""
    data = conn.memory["chan_data"]
    lines = list(dump_dict(data))
    print('\n'.join(lines))
    return "Printed {} channel records totalling {} lines of data to the console.".format(len(data), len(lines))


@hook.command(permissions=["botcontrol"], autohelp=False)
def dumpusers(conn):
    """- Dumps all stored user data for this connection to the console"""
    data = conn.memory["users"]
    lines = list(dump_dict(data))
    print('\n'.join(lines))
    return "Printed {} user records totalling {} lines of data to the console.".format(len(data), len(lines))


@hook.command(permissions=["botcontrol"], autohelp=False)
def updateusers(bot):
    """- Forces an update of all /NAMES data for all channels"""
    get_chan_data(bot)
    return "Updating all channel data"


@hook.irc_raw('JOIN')
def on_join(chan, nick, user, host, conn):
    if chan.startswith(':'):
        chan = chan[1:]

    users = conn.memory['users']
    user_data = WeakDict(nick=nick, user=user, host=host)
    user_data = users.setdefault(nick.casefold(), user_data)
    chan_data = conn.memory["chan_data"][chan]
    memb_data = WeakDict(chan=weakref.proxy(chan_data), user=user_data, status=[])
    chan_data["users"][nick.casefold()] = memb_data
    user_chans = user_data.setdefault("channels", WeakValueDictionary())
    user_chans[chan.casefold()] = memb_data


@hook.irc_raw('PART')
def on_part(chan, nick, conn):
    if chan.startswith(':'):
        chan = chan[1:]

    channels = conn.memory["chan_data"]
    nick_cf = nick.casefold()
    if nick_cf == conn.nick.casefold():
        try:
            del channels[chan]
        except KeyError:
            pass
    else:
        chan_data = channels[chan]
        try:
            del chan_data["users"][nick_cf]
        except KeyError:
            pass


@hook.irc_raw('KICK')
def on_kick(chan, target, conn):
    on_part(chan, target, conn)


@hook.irc_raw('QUIT')
def on_quit(nick, conn):
    nick_cf = nick.casefold()
    users = conn.memory["users"]
    if nick_cf in users:
        user = users[nick_cf]
        for memb in user.get("channels", {}).values():
            chan = memb["chan"]
            chan["users"].pop(nick_cf)


@hook.irc_raw('MODE')
def on_mode(chan, irc_paramlist, conn):
    if chan.startswith(':'):
        chan = chan[1:]

    serv_info = conn.memory["server_info"]
    statuses = serv_info["statuses"]
    status_modes = {status.mode for status in statuses.values()}
    mode_types = serv_info["channel_modes"]
    chans = conn.memory["chan_data"]
    if chan not in chans:
        return

    chan_data = chans[chan]

    modes = irc_paramlist[1]
    mode_params = irc_paramlist[2:]
    new_modes = {}
    adding = True
    for c in modes:
        if c == '+':
            adding = True
        elif c == '-':
            adding = False
        else:
            new_modes[c] = adding
            is_status = c in status_modes
            mode_type = mode_types.get(c)
            if mode_type:
                mode_type = mode_type.type
            else:
                mode_type = 'B' if is_status else None

            if mode_type in "AB" or (mode_type == 'C' and adding):
                param = mode_params.pop(0)

                if is_status:
                    memb = chan_data["users"][param.casefold()]
                    status = statuses[c]
                    if adding:
                        memb["status"].append(status)
                        memb["status"].sort(key=attrgetter("level"), reverse=True)
                    else:
                        if status in memb["status"]:
                            memb["status"].remove(status)


@hook.irc_raw('NICK')
def on_nick(nick, irc_paramlist, conn):
    users = conn.memory["users"]
    nick_cf = nick.casefold()
    new_nick = irc_paramlist[0]
    if new_nick.startswith(':'):
        new_nick = new_nick[1:]

    new_nick_cf = new_nick.casefold()
    user = users.pop(nick_cf)
    users[new_nick_cf] = user
    user["nick"] = nick
    for memb in user["channels"].values():
        chan_users = memb["chan"]["users"]
        chan_users[new_nick_cf] = chan_users.pop(nick_cf)
