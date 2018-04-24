"""
Track channel ops for permissions checks

Requires:
server_info.py
"""
import asyncio
import warnings
import weakref
from operator import attrgetter
from weakref import WeakValueDictionary

from cloudbot import hook
from cloudbot.clients.irc.parser import Prefix
from cloudbot.util import formatting

lock = asyncio.Lock()


class KeyFoldMixin:
    def __contains__(self, item):
        return super().__contains__(item.casefold())

    def __getitem__(self, item):
        return super().__getitem__(item.casefold())

    def __setitem__(self, key, value):
        return super().__setitem__(key.casefold(), value)

    def __delitem__(self, key):
        return super().__delitem__(key.casefold())

    def pop(self, key, *args):
        try:
            o = self[key]
        except KeyError as e:
            if args:
                return args[0]

            raise e
        else:
            del self[key]
            return o

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default
            return default

    def update(*args, **kwargs):
        if not args:
            raise TypeError("'update' method missing 'self' parameter")

        self, *args = args
        if len(args) > 1:
            raise TypeError("At most 1 positional argument expected")

        if args:
            d = args[0]
            if hasattr(d, 'keys'):
                for k in d:
                    self[k] = d[k]
            else:
                for k, v in d:
                    self[k] = v

        if kwargs:
            self.update(kwargs)


class KeyFoldDict(KeyFoldMixin, dict):
    pass


class KeyFoldWeakValueDict(KeyFoldMixin, WeakValueDictionary):
    pass


class ChanDict(KeyFoldDict):
    def getchan(self, name):
        """
        :type name: str
        :rtype: Channel
        """
        try:
            return self[name]
        except KeyError:
            self[name] = value = Channel(name)
            return value


class UsersDict(KeyFoldWeakValueDict):
    def getuser(self, nick, user=None, host=None):
        """
        :type nick: str
        :type user: str
        :type host: str
        :rtype: User
        """
        try:
            return self[nick]
        except KeyError:
            self[nick] = value = User(nick, user, host)
            return value

    def merge_user(self, new_user):
        """
        :type new_user: User
        :rtype: User
        """
        try:
            old_user = self[new_user.nick]
        except KeyError:
            self[new_user.nick] = new_user
            return new_user

        if new_user.ident is not None:
            old_user.ident = new_user.ident

        if new_user.host is not None:
            old_user.host = new_user.host

        old_user.data.update(new_user.data)

        return old_user


class BaseData:
    def __init__(self):
        self.data = {}

    def __getitem__(self, item):
        warnings.warn(
            "Access to data fields via __getitem__ has been deprecated inb favor of accessing the .data attribute",
            DeprecationWarning
        )
        try:
            return getattr(self, item)
        except AttributeError:
            return self.data[item]

    def __setitem__(self, key, value):
        warnings.warn(
            "Access to data fields via __setitem__ has been deprecated inb favor of accessing the .data attribute",
            DeprecationWarning
        )
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            self.data[key] = value


class User(BaseData):
    """
    :type nick: str
    :type ident: str | None
    :type host: str | None
    :type channels: dict[str, ChannelMember]
    """

    def __init__(self, nick, ident=None, host=None):
        super().__init__()

        self.nick = nick
        self.ident = ident
        self.host = host
        self.channels = KeyFoldWeakValueDict()

        self.is_away = False
        self.away_message = None

        self.is_oper = False

        self.realname = None

        self.server = None

        self._account = None

    @property
    def account(self):
        return self._account

    @account.setter
    def account(self, value):
        if value == "*":
            self._account = None
        else:
            self._account = value

    @property
    def mask(self):
        out = self.nick
        if self.ident is not None:
            out += '!' + self.ident

        if self.host is not None:
            out += '@' + self.host

        return out

    def add_channel(self, chan):
        """
        :type chan: Channel
        :rtype: ChannelMember
        """
        return chan.add_user(self)


class Channel(BaseData):
    """
    :type name: str
    :type users: dict[str, ChannelMember]
    """

    def __init__(self, name):
        super().__init__()

        self.name = name
        self.users = KeyFoldDict()

        self.receiving_names = False

    def get_member(self, name):
        """
        :type name: str
        :rtype: ChannelMember
        """
        return self.users[name]

    def add_user(self, user):
        """
        :type user: User
        :rtype: ChannelMember
        """
        member = ChannelMember(user, self)
        self.users[user.nick] = member
        user.channels[self.name] = member
        return member


class ChannelMember(BaseData):
    """
    :type user: User
    :type channel: Channel
    :type status: list[plugins.core.server_info.Status]
    """

    def __init__(self, user, channel):
        super().__init__()

        self.user = user
        self.channel = weakref.proxy(channel)
        self.status = []


def get_users(conn):
    """
    :type conn: cloudbot.client.Client
    :rtype: UsersDict
    """
    return conn.memory["users"]


def get_user(conn, name):
    """
    :type conn: cloudbot.client.Client
    :type name: str
    :rtype: User
    """
    return get_users(conn)[name]


def get_channels(conn):
    """
    :type conn: cloudbot.client.Client
    :rtype: ChanDict
    """
    return conn.memory["chan_data"]


def get_channel(conn, name):
    """
    :type conn: cloudbot.client.Client
    :type name: str
    :rtype: Channel
    """
    return get_channels(conn)[name]


def update_chan_data(conn, chan):
    chan_data = get_channels(conn).getchan(chan)
    chan_data.data["receiving_names"] = False
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


def is_cap_enabled(conn, cap):
    try:
        caps = conn.memory["server_caps"]
    except LookupError:
        return False

    return caps.is_cap_enabled(cap)


@hook.on_start
def get_chan_data(bot):
    """
    :type bot: cloudbot.bot.CloudBot
    """
    for conn in bot.connections.values():
        if conn.connected and conn.type == 'irc':
            init_chan_data(conn, False)
            update_conn_data(conn)


@hook.connect(clients='irc')
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


def get_conn_statuses(conn):
    """
    :type conn: cloudbot.client.Client
    :rtype: dict[str, plugins.core.server_info.Status]
    """
    return {status.prefix: status for status in set(conn.memory["server_info"]["statuses"].values())}


def replace_user_data(conn, chan_data):
    """
    :type conn: cloudbot.client.Client
    :type chan_data: Channel
    """
    statuses = get_conn_statuses(conn)
    global_users = get_users(conn)

    # Remove and store the old user data
    old_members = chan_data.users.copy()
    chan_data.users.clear()

    names_data = chan_data.data.pop("new_users", [])
    has_uh_i_n = is_cap_enabled(conn, "userhost-in-names")
    has_multi_pfx = is_cap_enabled(conn, "multi-prefix")

    for name in names_data:
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

        if has_uh_i_n:
            pfx = Prefix.parse(name)
            user = User(pfx.nick, pfx.user, pfx.host)
        else:
            user = User(name)

        user = global_users.merge_user(user)

        member = user.add_channel(chan_data)

        member.status.clear()
        member.status.extend(user_statuses)

        try:
            old_data = old_members[user.nick]
        except KeyError:
            pass
        else:
            member.data.update(old_data.data)


@hook.irc_raw(['353', '366'], singlethread=True, lock=lock)
def on_names(conn, irc_paramlist, irc_command):
    chan = irc_paramlist[2 if irc_command == '353' else 1]
    chan_data = get_channels(conn).getchan(chan)
    if irc_command == '366':
        chan_data.receiving_names = False
        replace_user_data(conn, chan_data)
        return

    users = chan_data.data.setdefault("new_users", [])
    if not chan_data.receiving_names:
        chan_data.receiving_names = True
        users.clear()

    names = irc_paramlist[-1]
    if names.startswith(':'):
        names = names[1:].strip()

    users.extend(names.split())


@hook.permission("chanop", singlethread=True, lock=lock)
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


@hook.irc_raw('JOIN', singlethread=True, lock=lock)
def on_join(nick, user, host, conn, irc_paramlist):
    chan, *other_data = irc_paramlist

    if chan.startswith(':'):
        chan = chan[1:]

    users = get_users(conn)
    user = users.getuser(nick, user, host)

    chans = get_channels(conn)
    chan_data = chans.getchan(chan)

    user.add_channel(chan_data)

    if is_cap_enabled(conn, "extended-join") and other_data:
        acct, realname = other_data
        if acct == "*":
            acct = None

        user.data.update(account=acct, realname=realname)


@hook.irc_raw('MODE', singlethread=True, lock=lock)
def on_mode(chan, irc_paramlist, conn):
    if chan.startswith(':'):
        chan = chan[1:]

    try:
        chan_data = get_channel(conn, chan)
    except KeyError:
        return

    serv_info = conn.memory["server_info"]
    statuses = serv_info["statuses"]
    status_modes = {status.mode for status in statuses.values()}
    mode_types = serv_info["channel_modes"]

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
                    member = chan_data.get_member(param)
                    # memb = chan_users[param]
                    status = statuses[c]
                    memb_status = member.status
                    if adding == (status in memb_status):
                        raise ValueError("Attempted to add status {!r} to {!r} in {!r}".format(
                            status, param, chan
                        ))

                    if adding:
                        memb_status.append(status)
                        memb_status.sort(key=attrgetter("level"), reverse=True)
                    else:
                        memb_status.remove(status)


@hook.irc_raw('PART', singlethread=True, lock=lock)
def on_part(chan, nick, conn):
    if chan.startswith(':'):
        chan = chan[1:]

    channels = get_channels(conn)
    if nick.casefold() == conn.nick.casefold():
        del channels[chan]
    else:
        chan_data = channels[chan]
        del chan_data["users"][nick]


@hook.irc_raw('KICK', singlethread=True, lock=lock)
def on_kick(chan, target, conn):
    on_part(chan, target, conn)


@hook.irc_raw('QUIT', singlethread=True, lock=lock)
def on_quit(nick, conn):
    user = get_user(conn, nick)
    for memb in user.channels.values():
        chan = memb.channel
        del chan.users[nick]


@hook.irc_raw('NICK', singlethread=True, lock=lock)
def on_nick(nick, irc_paramlist, conn):
    users = get_users(conn)
    new_nick = irc_paramlist[0]
    if new_nick.startswith(':'):
        new_nick = new_nick[1:]

    user = users.pop(nick)
    users[new_nick] = user
    user.nick = new_nick

    for memb in user.channels.values():
        chan_users = memb.channel.users
        chan_users[new_nick] = chan_users.pop(nick)


@hook.irc_raw('ACCOUNT', singlethread=True, lock=lock)
def on_account(conn, nick, irc_paramlist):
    get_user(conn, nick).account = irc_paramlist[0]


@hook.irc_raw('CHGHOST', singlethread=True, lock=lock)
def on_chghost(conn, nick, irc_paramlist):
    ident, host = irc_paramlist
    user = get_user(conn, nick)
    user.ident = ident
    user.host = host


@hook.irc_raw('AWAY', singlethread=True, lock=lock)
def on_away(conn, nick, irc_paramlist):
    if irc_paramlist:
        reason = irc_paramlist[0]
    else:
        reason = None

    user = get_user(conn, nick)
    user.is_away = bool(reason)
    user.away_message = reason or None


@hook.irc_raw('352', singlethread=True, lock=lock)
def on_who(conn, irc_paramlist):
    _, _, ident, host, server, nick, status, realname = irc_paramlist
    realname = realname.split(None, 1)[1]
    user = get_user(conn, nick)
    status = list(status)
    is_away = status.pop(0) == "G"
    is_oper = status[:1] == "*"

    user.ident = ident
    user.host = host

    user.server = server

    user.realname = realname

    user.is_away = is_away
    user.is_oper = is_oper


@hook.irc_raw('311', singlethread=True, lock=lock)
def on_whois_name(conn, irc_paramlist):
    _, nick, ident, host, _, realname = irc_paramlist
    user = get_user(conn, nick)
    user.ident = ident
    user.host = host
    user.realname = realname


@hook.irc_raw('330', singlethread=True, lock=lock)
def on_whois_acct(conn, irc_paramlist):
    _, nick, acct = irc_paramlist[:2]
    get_user(conn, nick).account = acct


@hook.irc_raw('301', singlethread=True, lock=lock)
def on_whois_away(conn, irc_paramlist):
    _, nick, msg = irc_paramlist
    user = get_user(conn, nick)
    user.is_away = True
    user.away_message = msg


@hook.irc_raw('312', singlethread=True, lock=lock)
def on_whois_server(conn, irc_paramlist):
    _, nick, server, _ = irc_paramlist
    get_user(conn, nick).server = server


@hook.irc_raw('313', singlethread=True, lock=lock)
def on_whois_oper(conn, irc_paramlist):
    nick = irc_paramlist[1]
    get_user(conn, nick).is_oper = True


@hook.command("listchannelusers", singlethread=True, lock=lock)
def list_channel_users(conn, chan):
    def _format_user(user):
        return user.nick[:1] + "\u200b" + user.nick[1:]

    nicks = [
        _format_user(member.user)
        for member in get_channel(conn, chan).users.values()
    ]
    return formatting.get_text_list(nicks, 'and')
