from fnmatch import fnmatch

from sqlalchemy import Table, Column, UniqueConstraint, PrimaryKeyConstraint, String, Boolean

from cloudbot import hook
from cloudbot.util import database, web
from cloudbot.util.formatting import gen_markdown_table
from cloudbot.util.web import FileTypes

table = Table(
    "ignored",
    database.metadata,
    Column("connection", String(25)),
    Column("channel", String(25)),
    Column("mask", String(250)),
    Column("status", Boolean, default=True),
    UniqueConstraint("connection", "channel", "mask", "status"),
    PrimaryKeyConstraint("connection", "channel", "mask")
)


@hook.on_start
def load_cache(event):
    global ignore_cache
    ignore_cache = []

    with event.db_session() as db:
        rows = db.execute(table.select()).fetchall()

    for row in rows:
        conn = row["connection"]
        chan = row["channel"]
        mask = row["mask"]
        ignore_cache.append((conn, chan, mask))


def add_ignore(event, conn, chan, mask):
    if (conn, chan) in ignore_cache:
        return

    with event.db_session() as db:
        db.execute(table.insert().values(connection=conn, channel=chan, mask=mask))
        db.commit()

    load_cache(event)


def remove_ignore(event, conn, chan, mask):
    with event.db_session() as db:
        db.execute(table.delete().where(table.c.connection == conn).where(table.c.channel == chan)
                   .where(table.c.mask == mask))
        db.commit()

    load_cache(event)


def is_ignored(conn, chan, mask, wild_match=True):
    if wild_match:
        _match = fnmatch
    else:
        def _match(a, b):
            return a == b

    mask_cf = mask.casefold()
    for _conn, _chan, _mask in ignore_cache:
        _mask_cf = _mask.casefold()
        if _chan == "*":
            # this is a global ignore
            if _match(mask_cf, _mask_cf):
                return True
        else:
            # this is a channel-specific ignore
            if not (conn, chan) == (_conn, _chan):
                continue
            if _match(mask_cf, _mask_cf):
                return True


@hook.sieve(priority=50)
def ignore_sieve(event):
    """
    :type event: cloudbot.event.Event
    """
    _hook = event.hook

    # don't block event hooks
    if _hook.type in ("irc_raw", "event"):
        return event

    # don't block an event that could be unignoring
    if _hook.type == "command" and event.triggered_command in ("unignore", "global_unignore"):
        return event

    if event.mask is None:
        # this is a server message, we don't need to check it
        return event

    if is_ignored(event.conn.name, event.chan, event.mask):
        return None

    return event


def get_user(conn, text):
    users = conn.memory.get("users", {})
    user = users.get(text)

    if user is None:
        mask = text
    else:
        mask = "*!*@{host}".format_map(user)

    if '@' not in mask:
        mask += "!*@*"

    return mask


global_ignore_perms = ["botcontrol"]
channel_ignore_perms = global_ignore_perms + ["ignore", "chanop"]


@hook.command(permissions=channel_ignore_perms)
def ignore(text, chan, conn, notice, admin_log, nick, event):
    """<nick|mask> -- ignores all input from <nick|mask> in this channel."""
    target = get_user(conn, text)

    if is_ignored(conn.name, chan, target, False):
        notice("{} is already ignored in {}.".format(target, chan))
    else:
        admin_log("{} used IGNORE to make me ignore {} in {}".format(nick, target, chan))
        notice("{} has been ignored in {}.".format(target, chan))
        add_ignore(event, conn.name, chan, target)


@hook.command(permissions=channel_ignore_perms)
def unignore(text, chan, conn, notice, nick, admin_log, event):
    """<nick|mask> -- un-ignores all input from <nick|mask> in this channel."""
    target = get_user(conn, text)

    if not is_ignored(conn.name, chan, target, False):
        notice("{} is not ignored in {}.".format(target, chan))
    else:
        admin_log("{} used UNIGNORE to make me stop ignoring {} in {}".format(nick, target, chan))
        notice("{} has been un-ignored in {}.".format(target, chan))
        remove_ignore(event, conn.name, chan, target)


@hook.command(permissions=global_ignore_perms)
def global_ignore(text, conn, notice, nick, admin_log, event):
    """<nick|mask> -- ignores all input from <nick|mask> in ALL channels."""
    target = get_user(conn, text)

    if is_ignored(conn.name, "*", target, False):
        notice("{} is already globally ignored.".format(target))
    else:
        notice("{} has been globally ignored.".format(target))
        admin_log("{} used GLOBAL_IGNORE to make me ignore {} everywhere".format(nick, target))
        add_ignore(event, conn.name, "*", target)


@hook.command(permissions=global_ignore_perms)
def global_unignore(text, conn, notice, nick, admin_log, event):
    """<nick|mask> -- un-ignores all input from <nick|mask> in ALL channels."""
    target = get_user(conn, text)

    if not is_ignored(conn.name, "*", target, False):
        notice("{} is not globally ignored.".format(target))
    else:
        notice("{} has been globally un-ignored.".format(target))
        admin_log("{} used GLOBAL_UNIGNORE to make me stop ignoring {} everywhere".format(nick, target))
        remove_ignore(event, conn.name, "*", target)


def _markdown_escape(text):
    return text.replace('*', '\\*')


def _escape_values(values):
    for value in values:
        yield _markdown_escape(value)


def paste_ignore_list(network=None, chan=None):
    if network is None:
        assert chan is None

    ignores = [
        _ignore for _ignore in ignore_cache
        if (
            (network is None or _ignore[0] == network) and
            (chan is None or _ignore[1] == chan)
        )
    ]

    if not ignores:
        return "No results."

    if network is None:  # Listing all ignores on this bot
        headers = ["Network", "Channel", "Mask"]
        header = "Bot-wide ignore list"
    elif chan is None:  # Listing all ignores for this network
        headers = ["Channel", "Mask"]
        ignores = [_ignore[1:] for _ignore in ignores]
        header = "Ignore list for {}".format(network)
    else:
        headers = ["Mask"]
        ignores = [_ignore[2:] for _ignore in ignores]
        if chan == "*":
            header = "Global ignore list for {}".format(network)
        else:
            header = "Ignore list for {}".format(chan)

    escaped_ignores = [
        tuple(_escape_values(row))
        for row in ignores
    ]

    out = gen_markdown_table(headers, escaped_ignores)
    text = "## " + header + "\n" + out

    return web.paste(text, FileTypes.MARKDOWN)


@hook.command("listignores", autohelp=False, permissions=channel_ignore_perms)
def list_ignores(conn, chan, text):
    """[channel] - View the ignores list for [channel] or the current channel if none is specified"""
    if text:
        channel = text
    else:
        channel = chan

    return paste_ignore_list(conn.name.casefold(), channel.casefold())


@hook.command("listglobalignores", autohelp=False, permissions=global_ignore_perms + ["snoonetstaff"])
def list_global_ignores(conn):
    """- List all global ignores for this network"""
    return paste_ignore_list(conn.name.casefold(), "*")


@hook.command("listallignores", autohelp=False, permissions=global_ignore_perms)
def list_all_ignores():
    return paste_ignore_list()
