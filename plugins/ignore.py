import asyncio
from fnmatch import fnmatch

from sqlalchemy import (
    Boolean,
    Column,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
)

from cloudbot import hook
from cloudbot.util import database

table = Table(
    "ignored",
    database.metadata,
    Column("connection", String(25)),
    Column("channel", String(25)),
    Column("mask", String(250)),
    Column("status", Boolean, default=True),
    UniqueConstraint("connection", "channel", "mask", "status"),
    PrimaryKeyConstraint("connection", "channel", "mask"),
)


@hook.on_start
def load_cache(db):
    """
    :type db: sqlalchemy.orm.Session
    """
    global ignore_cache
    ignore_cache = []
    for row in db.execute(table.select()):
        conn = row["connection"]
        chan = row["channel"]
        mask = row["mask"]
        ignore_cache.append((conn, chan, mask))


def add_ignore(db, conn, chan, mask):
    if (conn, chan) in ignore_cache:
        pass
    else:
        db.execute(
            table.insert().values(connection=conn, channel=chan, mask=mask)
        )

    db.commit()
    load_cache(db)


def remove_ignore(db, conn, chan, mask):
    db.execute(
        table.delete()
        .where(table.c.connection == conn)
        .where(table.c.channel == chan)
        .where(table.c.mask == mask)
    )
    db.commit()
    load_cache(db)


def is_ignored(conn, chan, mask):
    mask_cf = mask.casefold()
    for _conn, _chan, _mask in ignore_cache:
        _mask_cf = _mask.casefold()
        if _chan == "*":
            # this is a global ignore
            if fnmatch(mask_cf, _mask_cf):
                return True
        else:
            # this is a channel-specific ignore
            if not (conn, chan) == (_conn, _chan):
                continue
            if fnmatch(mask_cf, _mask_cf):
                return True


# noinspection PyUnusedLocal
@hook.sieve(priority=50)
@asyncio.coroutine
def ignore_sieve(bot, event, _hook):
    """
    :type bot: cloudbot.bot.CloudBot
    :type event: cloudbot.event.Event
    :type _hook: cloudbot.plugin.Hook
    """
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
    """<nick|mask> -- ignores all input from <nick|mask> in this channel."""
    target = get_user(conn, text)

    if is_ignored(conn.name, chan, target):
        notice(f"{target} is already ignored in {chan}.")
    else:
        admin_log(f"{nick} used IGNORE to make me ignore {target} in {chan}")
        notice(f"{target} has been ignored in {chan}.")
        add_ignore(db, conn.name, chan, target)


@hook.command(permissions=["ignore", "chanop"])
def unignore(text, db, chan, conn, notice, nick, admin_log):
    """<nick|mask> -- un-ignores all input from <nick|mask> in this channel."""
    target = get_user(conn, text)

    if not is_ignored(conn.name, chan, target):
        notice(f"{target} is not ignored in {chan}.")
    else:
        admin_log(
            f"{nick} used UNIGNORE to make me stop ignoring {target} in {chan}"
        )
        notice(f"{target} has been un-ignored in {chan}.")
        remove_ignore(db, conn.name, chan, target)


@hook.command(permissions=["botcontrol"])
def global_ignore(text, db, conn, notice, nick, admin_log):
    """<nick|mask> -- ignores all input from <nick|mask> in ALL channels."""
    target = get_user(conn, text)

    if is_ignored(conn.name, "*", target):
        notice(f"{target} is already globally ignored.")
    else:
        notice(f"{target} has been globally ignored.")
        admin_log(
            f"{nick} used GLOBAL_IGNORE to make me ignore {target} everywhere"
        )
        add_ignore(db, conn.name, "*", target)


@hook.command(permissions=["botcontrol"])
def global_unignore(text, db, conn, notice, nick, admin_log):
    """<nick|mask> -- un-ignores all input from <nick|mask> in ALL channels."""
    target = get_user(conn, text)

    if not is_ignored(conn.name, "*", target):
        notice(f"{target} is not globally ignored.")
    else:
        notice(f"{target} has been globally un-ignored.")
        admin_log(
            f"{nick} used GLOBAL_UNIGNORE to make me stop ignoring {target} everywhere"
        )
        remove_ignore(db, conn.name, "*", target)
