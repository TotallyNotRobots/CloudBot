"""
Track channel ops for permissions checks

Requires:
server_info.py
"""
import gc
import weakref
from collections import Mapping
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
        return super().__setitem__(key.casefold(), value)

    def __delitem__(self, key):
        return super().__delitem__(key.casefold())

    def pop(self, key, *args, **kwargs):
        return super().pop(key.casefold(), *args, **kwargs)

    def get(self, key, default=None):
        return super().get(key, default)

    def setdefault(self, key, default=None):
        return super().setdefault(key, default)


class KeyFoldDict(KeyFoldMixin, dict):
    pass


class KeyFoldWeakValueDict(KeyFoldMixin, WeakValueDictionary):
    pass


class ChanDict(KeyFoldDict):
    def getchan(self, name):
        try:
            return self[name]
        except KeyError:
            self[name] = value = WeakDict(name=name, users=KeyFoldDict())
            return value


class UsersDict(KeyFoldWeakValueDict):
    def getuser(self, nick):
        try:
            return self[nick]
        except KeyError:
            self[nick] = value = WeakDict(nick=nick, channels=KeyFoldWeakValueDict())
            return value


def update_chan_data(conn, chan):
    chan_data = conn.memory["chan_data"].getchan(chan)
    chan_data["receiving_names"] = False
    conn.cmd("NAMES", chan)


def update_conn_data(conn):
    for chan in set(conn.channels):
        update_chan_data(conn, chan)


SUPPORTED_CAPS = frozenset({
    "userhost-in-names",
    "multi-prefix",
    "extended-join",
    "account-notify",
    "away-notify",
    "chghost",
})


@hook.on_cap_available(*SUPPORTED_CAPS)
def do_caps():
    return True


def is_cap_available(conn, cap):
    caps = conn.memory.get("server_caps", {})
    return bool(caps.get(cap, False))


@hook.on_start
def get_chan_data(bot):
    for conn in bot.connections.values():
        if conn.connected:
            init_chan_data(conn, False)
            update_conn_data(conn)


def clean_user_data(user):
    for memb in user.get("channels", {}).values():
        status = list(set(memb.get("status", [])))
        status.sort(key=attrgetter("level"), reverse=True)
        memb["status"] = status


def clean_chan_data(chan):
    with suppress(KeyError):
        del chan["new_users"]

    with suppress(KeyError):
        del chan["receiving_names"]


def clean_conn_data(conn):
    for user in conn.memory.get("users", {}).values():
        clean_user_data(user)

    for chan in conn.memory.get("chan_data", {}).values():
        clean_chan_data(chan)


def clean_data(bot):
    for conn in bot.connections.values():
        clean_conn_data(conn)


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
    user["channels"][chan] = membership


def replace_user_data(conn, chan_data):
    statuses = {status.prefix: status for status in set(conn.memory["server_info"]["statuses"].values())}
    users = conn.memory["users"]
    old_users = chan_data["users"]
    new_data = chan_data.pop("new_users", [])
    new_users = KeyFoldDict()
    has_uh_i_n = is_cap_available(conn, "userhost-in-names")
    has_multi_pfx = is_cap_available(conn, "multi-prefix")
    for name in new_data:
        user_data = WeakDict(channels=KeyFoldWeakValueDict())
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
            user_data.update(nick=pfx.nick, ident=pfx.user, host=pfx.host)
        else:
            user_data["nick"] = name

        nick = user_data["nick"]
        new_users[nick] = memb_data
        if nick in old_users:
            old_data = old_users[nick]  # Old membership object
            old_data.update(memb_data)  # New data takes priority over old data
            memb_data.update(old_data)

        old_user_data = users.getuser(nick)
        user_data["channels"] = old_user_data["channels"]
        add_user_membership(user_data, chan_data["name"], memb_data)
        old_user_data.update(user_data)
        user_data = old_user_data
        memb_data["user"] = user_data

    old_users.clear()
    old_users.update(new_users)  # Reassigning the dict would break other references to the data, so just update instead


@hook.irc_raw(['353', '366'], singlethread=True)
def on_names(conn, irc_paramlist, irc_command):
    chan = irc_paramlist[2 if irc_command == '353' else 1]
    chan_data = conn.memory["chan_data"].getchan(chan)
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
        elif isinstance(value, Mapping):
            _objects.append(id(value))
            yield from dump_dict(value, indent=indent, level=level + 1, _objects=_objects)
        else:
            _objects.append(id(value))
            yield ((" " * (indent * (level + 1))) + "{}".format(value))


@hook.permission("chanop")
def perm_check(chan, conn, nick):
    if not (chan and conn):
        return False

    chans = conn.memory["chan_data"]
    try:
        chan_data = chans[chan]
    except KeyError:
        return False

    try:
        memb = chan_data["users"][nick]
    except KeyError:
        return False

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


@hook.command(permissions=["botcontrol"], autohelp=False)
def cleanusers(bot):
    clean_data(bot)
    gc.collect()
    return "Data cleaned."


@hook.command(permissions=["botcontrol"], autohelp=False)
def clearusers(bot):
    init_chan_data(bot, True)
    gc.collect()
    return "Data cleared."


@hook.irc_raw('JOIN')
def on_join(nick, user, host, conn, irc_paramlist):
    chan, *other_data = irc_paramlist

    if chan.startswith(':'):
        chan = chan[1:]

    data = {'ident': user, 'host': host}

    if is_cap_available(conn, "extended-join") and other_data:
        acct, realname = other_data
        if acct == "*":
            acct = None

        data.update(account=acct, realname=realname)

    users = conn.memory['users']

    user_data = users.getuser(nick)
    user_data.update(data)

    chan_data = conn.memory["chan_data"].getchan(chan)
    memb_data = WeakDict(chan=weakref.proxy(chan_data), user=user_data, status=[])
    chan_data["users"][nick] = memb_data
    add_user_membership(user_data, chan, memb_data)


@hook.irc_raw('MODE')
def on_mode(chan, irc_paramlist, conn):
    if chan.startswith(':'):
        chan = chan[1:]

    serv_info = conn.memory["server_info"]
    statuses = serv_info["statuses"]
    status_modes = {status.mode for status in statuses.values()}
    mode_types = serv_info["channel_modes"]
    chans = conn.memory["chan_data"]

    try:
        chan_data = chans[chan]
    except KeyError:
        return

    chan_users = chan_data["users"]
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
                    memb = chan_users[param]
                    status = statuses[c]
                    memb_status = memb["status"]
                    if adding:
                        memb_status.append(status)
                        memb_status.sort(key=attrgetter("level"), reverse=True)
                    else:
                        memb_status.remove(status)


@hook.irc_raw('PART')
def on_part(chan, nick, conn):
    if chan.startswith(':'):
        chan = chan[1:]

    channels = conn.memory["chan_data"]
    if nick.casefold() == conn.nick.casefold():
        del channels[chan]
    else:
        chan_data = channels[chan]
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
            del chan["users"][nick]


@hook.irc_raw('NICK')
def on_nick(nick, irc_paramlist, conn):
    users = conn.memory["users"]
    new_nick = irc_paramlist[0]
    if new_nick.startswith(':'):
        new_nick = new_nick[1:]

    user = users.pop(nick)
    users[new_nick] = user
    user["nick"] = new_nick
    for memb in user.get("channels", {}).values():
        chan_users = memb["chan"]["users"]
        chan_users[new_nick] = chan_users.pop(nick)


@hook.irc_raw('ACCOUNT')
def on_account(conn, nick, irc_paramlist):
    conn.memory["users"][nick]["account"] = irc_paramlist[0]


@hook.irc_raw('CHGHOST')
def on_chghost(conn, nick, irc_paramlist):
    ident, host = irc_paramlist
    conn.memory["users"][nick].update(ident=ident, host=host)


@hook.irc_raw('AWAY')
def on_away(conn, nick, irc_paramlist):
    if irc_paramlist:
        reason = irc_paramlist[0]
    else:
        reason = None

    conn.memory["users"][nick].update(is_away=(reason is not None), away_message=reason)


@hook.irc_raw('352')
def on_who(conn, irc_paramlist):
    _, _, ident, host, server, nick, status, realname = irc_paramlist
    realname = realname.split(None, 1)[1]
    user = conn.memory["users"][nick]
    status = list(status)
    is_away = status.pop(0) == "G"
    is_oper = status[:1] == "*"
    user.update(
        ident=ident,
        host=host,
        server=server,
        realname=realname,
        is_away=is_away,
        is_oper=is_oper,
    )


@hook.irc_raw('311')
def on_whois_name(conn, irc_paramlist):
    _, nick, ident, host, _, realname = irc_paramlist
    conn.memory["users"][nick].update(ident=ident, host=host, realname=realname)


@hook.irc_raw('330')
def on_whois_acct(conn, irc_paramlist):
    _, nick, acct = irc_paramlist[:2]
    conn.memory["users"][nick]["account"] = acct


@hook.irc_raw('301')
def on_whois_away(conn, irc_paramlist):
    _, nick, msg = irc_paramlist
    conn.memory["users"][nick].update(is_away=True, away_message=msg)


@hook.irc_raw('312')
def on_whois_server(conn, irc_paramlist):
    _, nick, server, _ = irc_paramlist
    conn.memory["users"][nick].update(server=server)


@hook.irc_raw('313')
def on_whois_oper(conn, irc_paramlist):
    nick = irc_paramlist[1]
    conn.memory["users"][nick].update(is_oper=True)
