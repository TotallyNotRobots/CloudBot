"""
Track channel ops for permissions checks

Requires:
server_info.py
"""
import weakref
from contextlib import suppress
from operator import attrgetter
from weakref import WeakValueDictionary

from cloudbot import hook
from cloudbot.util.parsers.irc import Prefix


class WeakDict(dict):
    # Subclass dict to allow it to be weakly referenced
    pass


class KeyFoldMixin:
    def __contains__(self, item):
        return super().__contains__(item.casefold())

    def __getitem__(self, item):
        return super().__getitem__(item.casefold())

    def __setitem__(self, key, value):
        super().__setitem__(key.casefold(), value)

    def __delitem__(self, key):
        super().__delitem__(key.casefold())


class KeyFoldDict(KeyFoldMixin, dict):
    pass


class KeyFoldWeakValueDict(KeyFoldMixin, WeakValueDictionary):
    def pop(self, key, *args):
        return super().pop(key.casefold(), *args)

    def get(self, key, default=None):
        return super().get(key.casefold(), default=default)

    def setdefault(self, key, default=None):
        return super().setdefault(key.casefold(), default=default)


class ChanDict(KeyFoldDict):
    __slots__ = ()

    def __missing__(self, key):
        data = WeakDict(name=key, users=KeyFoldDict())
        self[key] = data
        return data


class UsersDict(KeyFoldWeakValueDict):
    __slots__ = ()

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError:
            return self.__missing__(item)

    def __missing__(self, key):
        self[key] = value = WeakDict(nick=key, channels=KeyFoldWeakValueDict())
        return value


def update_chan_data(conn, chan):
    chan_data = conn.memory["chan_data"][chan]
    chan_data["receiving_names"] = False
    conn.cmd("NAMES", chan)


def update_conn_data(conn):
    for chan in set(conn.channels):
        update_chan_data(conn, chan)


@hook.on_cap_available("userhost-in-names", "multi-prefix")
def do_caps():
    return True


@hook.on_start
def get_chan_data(bot):
    for conn in bot.connections.values():
        if conn.connected:
            init_chan_data(conn, False)
            update_conn_data(conn)


@hook.connect
def init_chan_data(conn, _clear=True):
    chan_data = conn.memory.setdefault("chan_data", ChanDict())
    users = conn.memory.setdefault("users", UsersDict())

    if not (isinstance(chan_data, ChanDict) and isinstance(users, UsersDict)):
        del conn.memory["chan_data"]
        del conn.memory["users"]

        return init_chan_data(conn, _clear)

    if _clear:
        chan_data.clear()
        users.clear()


def add_user_membership(user, chan, membership):
    chans = user.setdefault('channels', KeyFoldWeakValueDict())
    chans[chan] = membership


def replace_user_data(conn, chan_data):
    statuses = {status.prefix: status for status in set(conn.memory["server_info"]["statuses"].values())}
    users = conn.memory["users"]
    old_users = chan_data['users']
    new_data = chan_data.pop("new_users", [])
    new_users = KeyFoldDict()
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
            pfx = Prefix.parse(name)
            user_data.update({"nick": pfx.nick, "ident": pfx.user, "host": pfx.host})
        else:
            user_data["nick"] = name

        nick = user_data["nick"]
        new_users[nick] = memb_data
        if nick in old_users:
            old_data = old_users[nick]
            old_data.update(memb_data)  # New data takes priority over old data
            memb_data.update(old_data)

        old_user_data = users.setdefault(nick, user_data)
        old_user_data.update(user_data)
        user_data = old_user_data
        memb_data["user"] = user_data
        add_user_membership(user_data, chan_data["name"], memb_data)

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
    if nick not in chan_data["users"]:
        return False

    memb = chan_data["users"][nick]
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


@hook.irc_raw(['JOIN', 'MODE'], singlethread=True)
def on_join_mode(chan, nick, user, host, conn, irc_command, irc_paramlist):
    """
    Both JOIN and MODE are handled in one hook with Hook:singlethread=True
    to ensure they are handled in order, avoiding a possible race condition
    """
    if irc_command == 'JOIN':
        return on_join(chan, nick, user, host, conn)
    elif irc_command == 'MODE':
        return on_mode(chan, irc_paramlist, conn)


def on_join(chan, nick, user, host, conn):
    if chan.startswith(':'):
        chan = chan[1:]

    users = conn.memory['users']
    user_data = users[nick]
    user_data.update(user=user, host=host)
    chan_data = conn.memory["chan_data"][chan]
    memb_data = WeakDict(chan=weakref.proxy(chan_data), user=user_data, status=[])
    chan_data["users"][nick] = memb_data
    add_user_membership(user_data, chan, memb_data)


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
                    memb = chan_data["users"][param]
                    status = statuses[c]
                    if adding:
                        memb["status"].append(status)
                        memb["status"].sort(key=attrgetter("level"), reverse=True)
                    else:
                        if status in memb["status"]:
                            memb["status"].remove(status)


@hook.irc_raw('PART')
def on_part(chan, nick, conn):
    if chan.startswith(':'):
        chan = chan[1:]

    channels = conn.memory["chan_data"]
    if nick.casefold() == conn.nick.casefold():
        with suppress(KeyError):
            del channels[chan]
    else:
        chan_data = channels[chan]
        with suppress(KeyError):
            del chan_data["users"][nick]


@hook.irc_raw('KICK')
def on_kick(chan, target, conn):
    on_part(chan, target, conn)


@hook.irc_raw('QUIT')
def on_quit(nick, conn):
    users = conn.memory["users"]
    if nick in users:
        user = users[nick]
        for memb in user.get("channels", {}).values():
            chan = memb["chan"]
            with suppress(KeyError):
                del chan["users"][nick]


@hook.irc_raw('NICK')
def on_nick(nick, irc_paramlist, conn):
    users = conn.memory["users"]
    new_nick = irc_paramlist[0]
    if new_nick.startswith(':'):
        new_nick = new_nick[1:]

    user = users.pop(nick)
    users[new_nick] = user
    user["nick"] = nick
    for memb in user.get("channels", {}).values():
        chan_users = memb["chan"]["users"]
        with suppress(KeyError):
            chan_users[new_nick] = chan_users.pop(nick)
