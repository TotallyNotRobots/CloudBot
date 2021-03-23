from collections import OrderedDict
from typing import Dict, List, Tuple

from irclib.util.compare import match_mask
from sqlalchemy import (
    Boolean,
    Column,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
    and_,
    select,
)

from cloudbot import hook
from cloudbot.util import database, web

table = Table(
    "ignored",
    database.metadata,
    Column("connection", String),
    Column("channel", String),
    Column("mask", String),
    Column("status", Boolean, default=True),
    UniqueConstraint("connection", "channel", "mask", "status"),
    PrimaryKeyConstraint("connection", "channel", "mask"),
)

ignore_cache: List[Tuple[str, str, str]] = []


@hook.on_start()
def load_cache(db):
    new_cache = []
    for row in db.execute(table.select()):
        conn = row["connection"]
        chan = row["channel"]
        mask = row["mask"]
        new_cache.append((conn, chan, mask))

    ignore_cache.clear()
    ignore_cache.extend(new_cache)


def find_ignore(conn, chan, mask):
    search = (conn.casefold(), chan.casefold(), mask.casefold())
    for _conn, _chan, _mask in ignore_cache:
        if search == (_conn.casefold(), _chan.casefold(), _mask.casefold()):
            return _conn, _chan, _mask

    return None


def ignore_in_cache(conn, chan, mask):
    if find_ignore(conn, chan, mask):
        return True

    return False


def add_ignore(db, conn, chan, mask):
    if ignore_in_cache(conn, chan, mask):
        return

    db.execute(table.insert().values(connection=conn, channel=chan, mask=mask))
    db.commit()
    load_cache(db)


def remove_ignore(db, conn, chan, mask):
    item = find_ignore(conn, chan, mask)
    if not item:
        return False

    conn, chan, mask = item
    clause = and_(
        table.c.connection == conn,
        table.c.channel == chan,
        table.c.mask == mask,
    )
    db.execute(table.delete().where(clause))
    db.commit()
    load_cache(db)

    return True


def is_ignored(conn, chan, mask):
    chan_key = (conn.casefold(), chan.casefold())
    mask_cf = mask.casefold()
    for _conn, _chan, _mask in ignore_cache:
        _mask_cf = _mask.casefold()
        if _chan == "*":
            # this is a global ignore
            if match_mask(mask_cf, _mask_cf):
                return True
        else:
            # this is a channel-specific ignore
            if chan_key != (_conn.casefold(), _chan.casefold()):
                continue

            if match_mask(mask_cf, _mask_cf):
                return True

    return False


# noinspection PyUnusedLocal
@hook.sieve(priority=50)
async def ignore_sieve(bot, event, _hook):
    # don't block event hooks
    if _hook.type in ("irc_raw", "event"):
        return event

    # don't block an event that could be unignoring
    if _hook.type == "command" and event.triggered_command in (
        "unignore",
        "global_unignore",
    ):
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

    if "@" not in mask:
        mask += "!*@*"

    return mask


@hook.command(permissions=["ignore", "chanop"])
def ignore(text, db, chan, conn, notice, admin_log, nick):
    """<nick|mask> - ignores all input from <nick|mask> in this channel."""
    target = get_user(conn, text)

    if ignore_in_cache(conn.name, chan, target):
        notice("{} is already ignored in {}.".format(target, chan))
    else:
        admin_log(
            "{} used IGNORE to make me ignore {} in {}".format(
                nick, target, chan
            )
        )
        notice("{} has been ignored in {}.".format(target, chan))
        add_ignore(db, conn.name, chan, target)


@hook.command(permissions=["ignore", "chanop"])
def unignore(text, db, chan, conn, notice, nick, admin_log):
    """<nick|mask> - un-ignores all input from <nick|mask> in this channel."""
    target = get_user(conn, text)

    if remove_ignore(db, conn.name, chan, target):
        admin_log(
            "{} used UNIGNORE to make me stop ignoring {} in {}".format(
                nick, target, chan
            )
        )
        notice("{} has been un-ignored in {}.".format(target, chan))
    else:
        notice("{} is not ignored in {}.".format(target, chan))


@hook.command(permissions=["ignore", "chanop"], autohelp=False)
def listignores(db, conn, chan):
    """- List all active ignores for the current channel"""

    rows = db.execute(
        select(
            [table.c.mask],
            and_(
                table.c.connection == conn.name.lower(),
                table.c.channel == chan.lower(),
            ),
        )
    ).fetchall()

    out = "\n".join(row["mask"] for row in rows) + "\n"

    return web.paste(out)


@hook.command(permissions=["botcontrol"])
def global_ignore(text, db, conn, notice, nick, admin_log):
    """<nick|mask> - ignores all input from <nick|mask> in ALL channels."""
    target = get_user(conn, text)

    if ignore_in_cache(conn.name, "*", target):
        notice("{} is already globally ignored.".format(target))
    else:
        notice("{} has been globally ignored.".format(target))
        admin_log(
            "{} used GLOBAL_IGNORE to make me ignore {} everywhere".format(
                nick, target
            )
        )
        add_ignore(db, conn.name, "*", target)


@hook.command(permissions=["botcontrol"])
def global_unignore(text, db, conn, notice, nick, admin_log):
    """<nick|mask> - un-ignores all input from <nick|mask> in ALL channels."""
    target = get_user(conn, text)

    if not ignore_in_cache(conn.name, "*", target):
        notice("{} is not globally ignored.".format(target))
    else:
        notice("{} has been globally un-ignored.".format(target))
        admin_log(
            "{} used GLOBAL_UNIGNORE to make me stop ignoring {} everywhere".format(
                nick, target
            )
        )
        remove_ignore(db, conn.name, "*", target)


@hook.command(permissions=["botcontrol", "snoonetstaff"], autohelp=False)
def list_global_ignores(db, conn):
    """- List all global ignores for the current network"""
    return listignores(db, conn, "*")


@hook.command(permissions=["botcontrol", "snoonetstaff"], autohelp=False)
def list_all_ignores(db, conn, text):
    """<chan> - List all ignores for <chan>, requires elevated permissions"""
    whereclause = table.c.connection == conn.name.lower()

    if text:
        whereclause = and_(whereclause, table.c.channel == text.lower())

    rows = db.execute(
        select([table.c.channel, table.c.mask], whereclause)
    ).fetchall()

    ignores: Dict[str, List[str]] = OrderedDict()

    for row in rows:
        ignores.setdefault(row["channel"], []).append(row["mask"])

    out = ""
    for chan, masks in ignores.items():
        out += "Ignores for {}:\n".format(chan)
        for mask in masks:
            out += "- {}\n".format(mask)

        out += "\n"

    return web.paste(out)
