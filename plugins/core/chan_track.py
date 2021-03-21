"""
Track channel ops for permissions checks

Requires:
server_info.py
"""
import gc
import json
import logging
import time
import weakref
from collections.abc import Iterable, Mapping
from contextlib import suppress
from numbers import Number
from operator import attrgetter
from typing import Dict

from irclib.parser import MessageTag, Prefix, TagList

import cloudbot.bot
from cloudbot import hook
from cloudbot.client import Client
from cloudbot.clients.irc import IrcClient
from cloudbot.hook import Priority
from cloudbot.util import web
from cloudbot.util.irc import ChannelMode, StatusMode, parse_mode_string
from cloudbot.util.mapping import KeyFoldDict, KeyFoldWeakValueDict

logger = logging.getLogger("cloudbot")


class MemberNotFoundException(KeyError):
    def __init__(self, name, chan):
        super().__init__(
            "No such member '{}' in channel '{}'".format(name, chan.name)
        )
        self.name = name
        self.chan = chan
        self.members = list(chan.users.values())
        self.nicks = [memb.user.nick for memb in self.members]
        self.masks = [memb.user.mask.mask for memb in self.members]


class ChannelMembersDict(KeyFoldDict):
    def __init__(self, chan):
        super().__init__()
        self.chan = weakref.ref(chan)

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError as e:
            raise MemberNotFoundException(item, self.chan()) from e

    def __delitem__(self, item):
        try:
            super().__delitem__(item)
        except KeyError as e:
            raise MemberNotFoundException(item, self.chan()) from e

    def pop(self, key, *args):
        try:
            return super().pop(key, *args)
        except KeyError as e:
            raise MemberNotFoundException(key, self.chan()) from e


class ChanDict(KeyFoldDict):
    """
    Mapping for channels on a network
    """

    def __init__(self, conn):
        super().__init__()

        self.conn = weakref.ref(conn)

    def getchan(self, name):
        try:
            return self[name]
        except KeyError:
            self[name] = value = Channel(name, self.conn())
            return value


class UsersDict(KeyFoldWeakValueDict):
    """
    Mapping for users on a network
    """

    def __init__(self, conn):
        super().__init__()

        self.conn = weakref.ref(conn)

    def getuser(self, nick):
        try:
            return self[nick]
        except KeyError:
            self[nick] = value = User(nick, self.conn())
            return value


class MappingAttributeAdapter:
    """
    Map item lookups to attribute lookups
    """

    def __init__(self):
        self.data = {}

    def __getitem__(self, item):
        try:
            return getattr(self, item)
        except AttributeError:
            return self.data[item]

    def __setitem__(self, key, value):
        if not hasattr(self, key):
            self.data[key] = value
        else:
            setattr(self, key, value)


class Channel(MappingAttributeAdapter):
    """
    Represents a channel and relevant data
    """

    class Member(MappingAttributeAdapter):
        """
        Store a user's membership with the channel
        """

        def __init__(self, user, channel):
            self.user = user
            self.channel = channel
            self.conn = user.conn
            self.status = []
            super().__init__()

        def add_status(self, status, sort=True):
            """
            Add a status to this membership
            """
            if status in self.status:
                logger.warning(
                    "[%s|chantrack] Attempted to add existing status "
                    "to channel member: %s %s",
                    self.conn.name,
                    self,
                    status,
                )
            else:
                self.status.append(status)
                if sort:
                    self.sort_status()

        def remove_status(self, status):
            if status not in self.status:
                logger.warning(
                    "[%s|chantrack] Attempted to remove status not set "
                    "on member: %s %s",
                    self.conn.name,
                    self,
                    status,
                )
            else:
                self.status.remove(status)

        def sort_status(self):
            """
            Ensure the status list is properly sorted
            """
            status = list(set(self.status))
            status.sort(key=attrgetter("level"), reverse=True)
            self.status = status

    def __init__(self, name, conn):
        super().__init__()
        self.name = name
        self.conn = weakref.proxy(conn)
        self.users = ChannelMembersDict(self)
        self.receiving_names = False

    def get_member(self, user, create=False):
        try:
            data = self.users[user.nick]
        except KeyError:
            if not create:
                raise

            self.users[user.nick] = data = self.Member(user, self)

        return data


class User(MappingAttributeAdapter):
    """
    Represent a user on a network
    """

    def __init__(self, name, conn):
        self.mask = Prefix(name)
        self.conn = weakref.proxy(conn)
        self.realname = None
        self._account = None
        self.server = None

        self.is_away = False
        self.away_message = None

        self.is_oper = False

        self.channels = KeyFoldWeakValueDict()
        super().__init__()

    def join_channel(self, channel):
        self.channels[channel.name] = memb = channel.get_member(
            self, create=True
        )
        return memb

    @property
    def account(self):
        """
        The user's nickserv account
        """
        return self._account

    @account.setter
    def account(self, value):
        if value == "*":
            value = None

        self._account = value

    @property
    def nick(self):
        """
        The user's nickname
        """
        return self.mask.nick

    @nick.setter
    def nick(self, value):
        self.mask = Prefix(value, self.ident, self.host)

    @property
    def ident(self):
        """
        The user's ident/username
        """
        return self.mask.user

    @ident.setter
    def ident(self, value):
        self.mask = Prefix(self.nick, value, self.host)

    @property
    def host(self):
        """
        The user's host/address
        """
        return self.mask.host

    @host.setter
    def host(self, value):
        self.mask = Prefix(self.nick, self.ident, value)


# region util functions


def get_users(conn):
    return conn.memory.setdefault("users", UsersDict(conn))


def get_chans(conn):
    return conn.memory.setdefault("chan_data", ChanDict(conn))


# endregion util functions


def update_chan_data(conn, chan):
    # type: (IrcClient, str) -> None
    """
    Start the process of updating channel data from /NAMES
    :param conn: The current connection
    :param chan: The channel to update
    """
    chan_data = get_chans(conn).getchan(chan)
    chan_data.receiving_names = False
    conn.cmd("NAMES", chan)


def update_conn_data(conn):
    # type: (IrcClient) -> None
    """
    Update all channel data for this connection
    :param conn: The connection to update
    """
    for chan in set(conn.channels):
        update_chan_data(conn, chan)


SUPPORTED_CAPS = frozenset(
    {
        "userhost-in-names",
        "multi-prefix",
        "extended-join",
        "account-notify",
        "away-notify",
        "chghost",
        "account-tag",
    }
)


@hook.on_cap_available(*SUPPORTED_CAPS)
def do_caps():
    """
    Request all available CAPs we support
    """
    return True


def is_cap_available(conn, cap):
    caps = conn.memory.get("server_caps", {})
    return bool(caps.get(cap, False))


@hook.on_start()
def get_chan_data(bot: cloudbot.bot.CloudBot):
    for conn in bot.connections.values():
        if conn.connected and conn.type == "irc":
            assert isinstance(conn, IrcClient)
            init_chan_data(conn, False)
            update_conn_data(conn)


def clean_user_data(user):
    for memb in user.channels.values():
        memb.sort_status()


def clean_chan_data(chan):
    with suppress(KeyError):
        del chan.data["new_users"]


def clean_conn_data(conn):
    for user in get_users(conn).values():
        clean_user_data(user)

    for chan in get_chans(conn).values():
        clean_chan_data(chan)


def clean_data(bot):
    for conn in bot.connections.values():
        clean_conn_data(conn)


@hook.connect()
def init_chan_data(conn, _clear=True):
    chan_data = get_chans(conn)
    users = get_users(conn)

    if not (isinstance(chan_data, ChanDict) and isinstance(users, UsersDict)):
        del conn.memory["chan_data"]
        del conn.memory["users"]

        return init_chan_data(conn, _clear)

    if _clear:
        chan_data.clear()
        users.clear()

    return None


def parse_names_item(item, statuses, has_multi_prefix, has_userhost):
    """
    Parse an entry from /NAMES
    :param item: The entry to parse
    :param statuses: Status prefixes on this network
    :param has_multi_prefix: Whether multi-prefix CAP is enabled
    :param has_userhost: Whether userhost-in-names CAP is enabled
    :return: The parsed data
    """
    user_status = []
    while item[:1] in statuses:
        status, item = item[:1], item[1:]
        user_status.append(statuses[status])
        if not has_multi_prefix:
            # Only remove one status prefix
            # if we don't have multi prefix enabled
            break

    user_status.sort(key=attrgetter("level"), reverse=True)

    if has_userhost:
        prefix = Prefix.parse(item)
    else:
        prefix = Prefix(item)

    return prefix.nick, prefix.user, prefix.host, user_status


def replace_user_data(conn, chan_data):
    statuses = {
        status.prefix: status
        for status in set(conn.memory["server_info"]["statuses"].values())
    }
    new_data = chan_data.data.pop("new_users", [])
    has_uh_i_n = is_cap_available(conn, "userhost-in-names")
    has_multi_pfx = is_cap_available(conn, "multi-prefix")
    old_data = chan_data.data.pop("old_users", {})
    new_names = set()

    for name in new_data:
        nick, ident, host, status = parse_names_item(
            name, statuses, has_multi_pfx, has_uh_i_n
        )

        new_names.update(nick.casefold())

        user_data = get_users(conn).getuser(nick)
        user_data.nick = nick
        if ident:
            user_data.ident = ident

        if host:
            user_data.host = host

        memb_data = user_data.join_channel(chan_data)
        memb_data.status = status

    for old_nick in old_data:
        if old_nick not in new_names:
            del chan_data.users[old_nick]


@hook.irc_raw(["353", "366"], singlethread=True, do_sieve=False)
def on_names(conn, irc_paramlist, irc_command):
    chan = irc_paramlist[2 if irc_command == "353" else 1]
    chan_data = get_chans(conn).getchan(chan)
    if irc_command == "366":
        chan_data.receiving_names = False
        replace_user_data(conn, chan_data)
        return

    users = chan_data.data.setdefault("new_users", [])
    if not chan_data.receiving_names:
        chan_data.data["old_users"] = old = ChannelMembersDict(chan_data)
        old.update(chan_data.users)

        chan_data.receiving_names = True
        users.clear()

    names = irc_paramlist[-1].strip()

    users.extend(names.split())


class MappingSerializer:
    """
    Serialize generic mappings to json
    """

    def __init__(self):
        self._seen_objects = []

    def _serialize(self, obj):
        if isinstance(obj, (str, Number, bool)) or obj is None:
            return obj

        if isinstance(obj, Client):
            return "<client name={!r}>".format(obj.name)

        if isinstance(obj, MappingAttributeAdapter):
            obj = vars(obj)

        if isinstance(obj, Mapping):
            if id(obj) in self._seen_objects:
                return "<{} with id {}>".format(type(obj).__name__, id(obj))

            self._seen_objects.append(id(obj))

            return {
                self._serialize(k): self._serialize(v) for k, v in obj.items()
            }

        if isinstance(obj, Iterable):
            if id(obj) in self._seen_objects:
                return "<{} with id {}>".format(type(obj).__name__, id(obj))

            self._seen_objects.append(id(obj))

            return [self._serialize(item) for item in obj]

        return repr(obj)

    def serialize(self, mapping, **kwargs):
        """
        Serialize mapping to JSON
        """
        return json.dumps(self._serialize(mapping), **kwargs)


@hook.permission("chanop")
def perm_check(chan, conn, nick):
    if not (chan and conn):
        return False

    chans = get_chans(conn)
    try:
        chan_data = chans[chan]
    except KeyError:
        return False

    try:
        memb = chan_data.users[nick]
    except KeyError:
        return False

    status = memb.status
    if status and status[0].level > 1:
        return True

    return False


@hook.command(permissions=["botcontrol"], autohelp=False)
def dumpchans(conn):
    """- Dumps all stored channel data for this connection to the console"""
    data = get_chans(conn)
    return web.paste(MappingSerializer().serialize(data, indent=2))


@hook.command(permissions=["botcontrol"], autohelp=False)
def dumpusers(conn):
    """- Dumps all stored user data for this connection to the console"""
    data = get_users(conn)
    return web.paste(MappingSerializer().serialize(data, indent=2))


@hook.command(permissions=["botcontrol"], autohelp=False)
def updateusers(bot):
    """- Forces an update of all /NAMES data for all channels"""
    get_chan_data(bot)
    return "Updating all channel data"


@hook.command(permissions=["botcontrol"], autohelp=False)
def cleanusers(bot):
    """- Clean user data"""
    clean_data(bot)
    gc.collect()
    return "Data cleaned."


@hook.command(permissions=["botcontrol"], autohelp=False)
def clearusers(bot):
    """- Clear all user data"""
    for conn in bot.connections.values():
        init_chan_data(conn)

    gc.collect()
    return "Data cleared."


@hook.command("getdata", permissions=["botcontrol"], autohelp=False)
def getdata_cmd(conn, chan, nick):
    """- Get data for current user"""
    chan_data = get_chans(conn).getchan(chan)
    user_data = get_users(conn).getuser(nick)
    memb = chan_data.get_member(user_data)
    return web.paste(MappingSerializer().serialize(memb, indent=2))


@hook.irc_raw("*", priority=Priority.HIGHEST, do_sieve=False)
def handle_tags(conn: IrcClient, nick: str, irc_tags: TagList) -> None:
    users = get_users(conn)

    if irc_tags:
        account_tag = irc_tags.get("account")  # type: MessageTag
        if account_tag:
            user_data = users.getuser(nick)
            user_data.account = account_tag.value


@hook.irc_raw(["PRIVMSG", "NOTICE"], do_sieve=False)
def on_msg(conn, nick, user, host, irc_paramlist):
    chan = irc_paramlist[0]

    if chan.lower() != conn.nick.lower():
        return

    users = get_users(conn)

    user_data = users.getuser(nick)

    user_data.ident = user
    user_data.host = host

    chan_data = get_chans(conn).getchan(chan)
    if nick not in chan_data.users:
        memb = user_data.join_channel(chan_data)
        conn.cmd("WHOIS", nick)
    else:
        memb = chan_data.get_member(user_data)

    memb.data["last_privmsg"] = time.time()


@hook.periodic(600)
def clean_pms(bot):
    cutoff = time.time() - 600
    for conn in bot.connections.values():
        pms = get_chans(conn).getchan(conn.nick)
        to_delete = set()
        for nick, memb in pms.users.items():
            if memb.data["last_privmsg"] < cutoff:
                to_delete.add(nick)

        for nick in to_delete:
            try:
                del pms.users[nick]
            except LookupError:
                pass


@hook.irc_raw("JOIN", do_sieve=False)
def on_join(nick, user, host, conn, irc_paramlist):
    chan, *other_data = irc_paramlist

    users = get_users(conn)

    user_data = users.getuser(nick)

    user_data.ident = user
    user_data.host = host

    if is_cap_available(conn, "extended-join") and other_data:
        acct, realname = other_data
        user_data.account = acct
        user_data.realname = realname

    chan_data = get_chans(conn).getchan(chan)
    user_data.join_channel(chan_data)


@hook.irc_raw("MODE", do_sieve=False)
def on_mode(chan, irc_paramlist, conn):
    if irc_paramlist[0].casefold() == conn.nick.casefold():
        # this is a user mode line
        return

    serv_info = conn.memory["server_info"]
    statuses = serv_info["statuses"]  # type: Dict[str, StatusMode]
    mode_types = serv_info["channel_modes"]  # type: Dict[str, ChannelMode]

    chan_data = get_chans(conn).getchan(chan)

    modes = irc_paramlist[1]
    mode_params = list(irc_paramlist[2:]).copy()
    new_modes = parse_mode_string(modes, mode_params, mode_types)
    new_statuses = [change for change in new_modes if change.is_status]
    to_sort = {}
    for change in new_statuses:
        status_char = change.char
        nick = change.param
        user = get_users(conn).getuser(nick)
        memb = chan_data.get_member(user, create=True)
        status = statuses[status_char]
        if change.adding:
            memb.add_status(status, sort=False)
            to_sort[user.nick] = memb
        else:
            memb.remove_status(status)

    for member in to_sort.values():
        member.sort_status()


@hook.irc_raw("PART", do_sieve=False)
def on_part(chan, nick, conn):
    channels = get_chans(conn)
    if nick.casefold() == conn.nick.casefold():
        del channels[chan]
    else:
        chan_data = channels[chan]
        del chan_data.users[nick]


@hook.irc_raw("KICK", do_sieve=False)
def on_kick(chan, target, conn):
    on_part(chan, target, conn)


@hook.irc_raw("QUIT", do_sieve=False)
def on_quit(nick, conn):
    users = get_users(conn)
    if nick in users:
        user = users.pop(nick)
        for memb in user.channels.values():
            chan = memb.channel
            del chan.users[nick]


@hook.irc_raw("NICK", do_sieve=False)
def on_nick(nick, irc_paramlist, conn):
    users = get_users(conn)
    chans = get_chans(conn)

    new_nick = irc_paramlist[0]

    user = users.pop(nick)
    users[new_nick] = user
    user.nick = new_nick
    for memb in user.channels.values():
        chan_users = memb.channel.users
        chan_users[new_nick] = chan_users.pop(nick)

    if conn.nick.lower() in (nick.lower(), new_nick.lower()) and nick in chans:
        chans[new_nick] = chans.pop(nick)
        pms = chans.getchan(new_nick)
        for memb in pms.users.values():
            user_chans = memb.user.channels
            user_chans[new_nick] = user_chans.pop(nick)


@hook.irc_raw("ACCOUNT", do_sieve=False)
def on_account(conn, nick, irc_paramlist):
    get_users(conn).getuser(nick).account = irc_paramlist[0]


@hook.irc_raw("CHGHOST", do_sieve=False)
def on_chghost(conn, nick, irc_paramlist):
    ident, host = irc_paramlist
    user = get_users(conn).getuser(nick)
    user.ident = ident
    user.host = host


@hook.irc_raw("AWAY", do_sieve=False)
def on_away(conn, nick, irc_paramlist):
    if irc_paramlist:
        reason = irc_paramlist[0]
    else:
        reason = None

    user = get_users(conn).getuser(nick)
    user.is_away = reason is not None
    user.away_message = reason


@hook.irc_raw("352", do_sieve=False)
def on_who(conn, irc_paramlist):
    _, _, ident, host, server, nick, status, realname = irc_paramlist
    realname = realname.split(None, 1)[1]
    user = get_users(conn).getuser(nick)
    status = list(status)
    is_away = status.pop(0) == "G"
    is_oper = status[:1] == "*"
    user.ident = ident
    user.host = host
    user.server = server
    user.realname = realname
    user.is_away = is_away
    user.is_oper = is_oper


@hook.irc_raw("311", do_sieve=False)
def on_whois_name(conn, irc_paramlist):
    _, nick, ident, host, _, realname = irc_paramlist
    user = get_users(conn).getuser(nick)
    user.ident = ident
    user.host = host
    user.realname = realname


@hook.irc_raw("330", do_sieve=False)
def on_whois_acct(conn, irc_paramlist):
    _, nick, acct = irc_paramlist[:3]
    get_users(conn).getuser(nick).account = acct


@hook.irc_raw("301", do_sieve=False)
def on_whois_away(conn, irc_paramlist):
    _, nick, msg = irc_paramlist
    user = get_users(conn).getuser(nick)
    user.is_away = True
    user.away_message = msg


@hook.irc_raw("312", do_sieve=False)
def on_whois_server(conn, irc_paramlist):
    _, nick, server, _ = irc_paramlist
    get_users(conn).getuser(nick).server = server


@hook.irc_raw("313", do_sieve=False)
def on_whois_oper(conn, irc_paramlist):
    nick = irc_paramlist[1]
    get_users(conn).getuser(nick).is_oper = True
