from collections import defaultdict
from datetime import datetime
from fnmatch import fnmatch

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    PrimaryKeyConstraint,
    String,
    Table,
    and_,
    not_,
)
from sqlalchemy.sql import select

from cloudbot import hook
from cloudbot.event import EventType
from cloudbot.util import database, timeformat, web
from cloudbot.util.formatting import gen_markdown_table

table = Table(
    "tells",
    database.metadata,
    Column("connection", String),
    Column("sender", String),
    Column("target", String),
    Column("message", String),
    Column("is_read", Boolean),
    Column("time_sent", DateTime),
    Column("time_read", DateTime),
)

disable_table = Table(
    "tell_ignores",
    database.metadata,
    Column("conn", String),
    Column("target", String),
    Column("setter", String),
    Column("set_at", DateTime),
    PrimaryKeyConstraint("conn", "target"),
)

ignore_table = Table(
    "tell_user_ignores",
    database.metadata,
    Column("conn", String),
    Column("set_at", DateTime),
    Column("nick", String),
    Column("mask", String),
    PrimaryKeyConstraint("conn", "nick", "mask"),
)

disable_cache = defaultdict(set)
ignore_cache = defaultdict(lambda: defaultdict(list))
tell_cache = []


@hook.on_start
def load_cache(db):
    """
    :type db: sqlalchemy.orm.Session
    """
    new_cache = []
    for row in db.execute(table.select().where(not_(table.c.is_read))):
        conn = row["connection"]
        target = row["target"]
        new_cache.append((conn, target))

    tell_cache.clear()
    tell_cache.extend(new_cache)


@hook.on_start
def load_disabled(db):
    """
    :type db: sqlalchemy.orm.Session
    """
    new_cache = defaultdict(set)
    for row in db.execute(disable_table.select()):
        new_cache[row["conn"]].add(row["target"].lower())

    disable_cache.clear()
    disable_cache.update(new_cache)


@hook.on_start
def load_ignores(db):
    """
    :type db: sqlalchemy.orm.Session
    """
    new_cache = defaultdict(lambda: defaultdict(list))
    for row in db.execute(ignore_table.select()):
        new_cache[row["conn"].lower()][row["nick"].lower()].append(row["mask"])

    ignore_cache.clear()
    ignore_cache.update(new_cache)


def is_disable(conn, target):
    """
    :type conn: cloudbot.client.Client
    :type target: str
    :rtype: bool
    """
    return target.lower() in disable_cache[conn.name.lower()]


def ignore_exists(conn, nick, mask):
    """
    :type conn: cloudbot.client.Client
    :type nick: str
    :type mask: str
    :rtype: bool
    """
    return mask in ignore_cache[conn.name.lower()][nick.lower()]


def can_send_to_user(conn, sender, target):
    """
    :type conn: cloudbot.client.Client
    :type sender: str
    :type target: str
    :rtype: bool
    """
    if target.lower() in disable_cache[conn.name.lower()]:
        return False

    for mask in ignore_cache[conn.name.lower()][target.lower()]:
        if fnmatch(sender, mask):
            return False

    return True


def add_disable(db, conn, setter, target, now=None):
    """
    :type db: sqlalchemy.orm.Session
    :type conn: cloudbot.client.Client
    :type setter: str
    :type target: str
    :type now: datetime
    """
    if now is None:
        now = datetime.now()

    db.execute(
        disable_table.insert().values(
            conn=conn.name.lower(), setter=setter, set_at=now, target=target.lower()
        )
    )
    db.commit()
    load_disabled(db)


def del_disable(db, conn, target):
    """
    :type db: sqlalchemy.orm.Session
    :type conn: cloudbot.client.Client
    :type target: str
    """
    db.execute(
        disable_table.delete().where(
            and_(
                disable_table.c.conn == conn.name.lower(),
                disable_table.c.target == target.lower(),
            )
        )
    )
    db.commit()
    load_disabled(db)


def list_disabled(db, conn):
    """
    :type db: sqlalchemy.orm.Session
    :type conn: cloudbot.client.Client
    """
    for row in db.execute(
        disable_table.select().where(disable_table.c.conn == conn.name.lower())
    ):
        yield (row["conn"], row["target"], row["setter"], row["set_at"].ctime())


def add_ignore(db, conn, nick, mask, now=None):
    """
    :type db: sqlalchemy.orm.Session
    :type conn: cloudbot.client.Client
    :type nick: str
    :type mask: str
    :type now: datetime
    """
    if now is None:
        now = datetime.now()

    db.execute(
        ignore_table.insert().values(
            conn=conn.name.lower(), set_at=now, nick=nick.lower(), mask=mask.lower()
        )
    )
    db.commit()
    load_ignores(db)


def del_ignore(db, conn, nick, mask):
    """
    :type db: sqlalchemy.orm.Session
    :type conn: cloudbot.client.Client
    :type nick: str
    :type mask: str
    """
    db.execute(
        ignore_table.delete().where(
            and_(
                ignore_table.c.conn == conn.name.lower(),
                ignore_table.c.nick == nick.lower(),
                ignore_table.c.mask == mask.lower(),
            )
        )
    )
    db.commit()
    load_ignores(db)


def list_ignores(conn, nick):
    """
    :type conn: cloudbot.client.Client
    :type nick: str
    """
    for mask in ignore_cache[conn.name.lower()][nick.lower()]:
        yield mask


def get_unread(db, server, target):
    """
    :type db: sqlalchemy.orm.Session
    :type server: str
    :type target: str
    """
    query = (
        select([table.c.sender, table.c.message, table.c.time_sent])
        .where(table.c.connection == server.lower())
        .where(table.c.target == target.lower())
        .where(not_(table.c.is_read))
        .order_by(table.c.time_sent)
    )
    return db.execute(query).fetchall()


def count_unread(db, server, target):
    query = (
        select([sa.func.count(table)])
        .where(table.c.connection == server.lower())
        .where(table.c.target == target.lower())
        .where(not_(table.c.is_read))
    )

    return db.execute(query).fetchone()[0]


def read_all_tells(db, server, target):
    query = (
        table.update()
        .where(table.c.connection == server.lower())
        .where(table.c.target == target.lower())
        .where(not_(table.c.is_read))
        .values(is_read=True)
    )
    db.execute(query)
    db.commit()
    load_cache(db)


def read_tell(db, server, target, message):
    query = (
        table.update()
        .where(table.c.connection == server.lower())
        .where(table.c.target == target.lower())
        .where(table.c.message == message)
        .values(is_read=True)
    )
    db.execute(query)
    db.commit()
    load_cache(db)


def add_tell(db, server, sender, target, message):
    query = table.insert().values(
        connection=server.lower(),
        sender=sender.lower(),
        target=target.lower(),
        message=message,
        is_read=False,
        time_sent=datetime.today(),
    )
    db.execute(query)
    db.commit()
    load_cache(db)


def tell_check(conn, nick):
    for _conn, _target in tell_cache:
        if (conn, nick.lower()) == (_conn, _target):
            return True


@hook.event([EventType.message, EventType.action], singlethread=True)
def tellinput(event, conn, db, nick, notice):
    """
    :type event: cloudbot.event.Event
    :type conn: cloudbot.client.Client
    :type db: sqlalchemy.orm.Session
    """
    if "showtells" in event.content.lower():
        return

    if tell_check(conn.name, nick):
        tells = get_unread(db, conn.name, nick)
    else:
        return

    if tells:
        user_from, message, time_sent = tells[0]
        reltime = timeformat.time_since(time_sent)

        if reltime == 0:
            reltime_formatted = "just a moment"
        else:
            reltime_formatted = reltime

        reply = "{} sent you a message {} ago: {}".format(
            user_from, reltime_formatted, message
        )
        if len(tells) > 1:
            reply += " (+{} more, {}showtells to view)".format(
                len(tells) - 1, conn.config["command_prefix"][0]
            )

        read_tell(db, conn.name, nick, message)
        notice(reply)


@hook.command(autohelp=False)
def showtells(nick, notice, db, conn):
    """- View all pending tell messages (sent in a notice)."""

    tells = get_unread(db, conn.name, nick)

    if not tells:
        notice("You have no pending messages.")
        return

    for tell in tells:
        sender, message, time_sent = tell
        past = timeformat.time_since(time_sent)
        notice("{} sent you a message {} ago: {}".format(sender, past, message))

    read_all_tells(db, conn.name, nick)


@hook.command("tell")
def tell_cmd(text, nick, db, conn, mask, event):
    """<nick> <message> - Relay <message> to <nick> when <nick> is around.

    :type text: str
    :type nick: str
    :type db: sqlalchemy.orm.Session
    :type conn: cloudbot.client.Client
    :type mask: str
    :type event: cloudbot.event.CommandEvent
    :rtype: None
    """
    query = text.split(" ", 1)

    if len(query) != 2:
        event.notice_doc()
        return

    target = query[0]
    message = query[1].strip()
    sender = nick

    if not can_send_to_user(conn, mask, target):
        event.notice("You may not send a tell to that user.")
        return

    if target.lower() == sender.lower():
        event.notice("Have you looked in a mirror lately?")
        return

    if not event.is_nick_valid(target.lower()) or target.lower() == conn.nick.lower():
        event.notice("Invalid nick '{}'.".format(target))
        return

    if count_unread(db, conn.name, target.lower()) >= 10:
        event.notice("Sorry, {} has too many messages queued already.".format(target))
        return

    add_tell(db, conn.name, sender, target.lower(), message)
    event.notice(
        "Your message has been saved, and {} will be notified once they are active.".format(
            target
        )
    )


def check_permissions(event, *perms):
    return any(event.has_permission(perm) for perm in perms)


@hook.command("telldisable", autohelp=False)
def tell_disable(conn, db, text, nick, event):
    """[nick] - Disable the sending of tells to [nick]"""
    is_self = False
    if not text or text.casefold() == nick.casefold():
        text = nick
        is_self = True
    elif not check_permissions(event, "botcontrol", "ignore"):
        event.notice("Sorry, you are not allowed to use this command.")
        return None

    target = text.split()[0]
    if is_disable(conn, target):
        return "Tells are already disabled for {}.".format(
            "you" if is_self else "{!r}".format(target)
        )

    add_disable(db, conn, nick, target)
    return "Tells are now disabled for {}.".format(
        "you" if is_self else "{!r}".format(target)
    )


@hook.command("tellenable", autohelp=False)
def tell_enable(conn, db, text, event, nick):
    """[nick] - Enable the sending of tells to [nick]"""
    is_self = False
    if not text or text.casefold() == nick.casefold():
        text = nick
        is_self = True
    elif not check_permissions(event, "botcontrol", "ignore"):
        event.notice("Sorry, you are not allowed to use this command.")
        return None

    target = text.split()[0]
    if not is_disable(conn, target):
        return "Tells are already enabled for {}.".format(
            "you" if is_self else "{!r}".format(target)
        )

    del_disable(db, conn, target)
    return "Tells are now enabled for {}.".format(
        "you" if is_self else "{!r}".format(target)
    )


@hook.command("listtelldisabled", permissions=["botcontrol", "ignore"], autohelp=False)
def list_tell_disabled(conn, db):
    """- Returns the current list of people who are not able to recieve tells"""
    ignores = list(list_disabled(db, conn))
    md = gen_markdown_table(["Connection", "Target", "Setter", "Set At"], ignores)
    return web.paste(md, "md", "hastebin")


@hook.command("tellignore")
def tell_ignore(db, conn, nick, text, notice):
    """<mask> - Disallow users matching <mask> from sending you tells"""
    mask = text.split()[0].lower()
    if ignore_exists(conn, nick, mask):
        notice("You are already ignoring tells from {!r}".format(mask))
        return

    add_ignore(db, conn, nick, mask)
    notice("You are now ignoring tells from {!r}".format(mask))


@hook.command("tellunignore")
def tell_unignore(db, conn, nick, text, notice):
    """<mask> - Remove a tell ignore"""
    mask = text.split()[0].lower()
    if not ignore_exists(conn, nick, mask):
        notice("No ignore matching {!r} exists.".format(mask))
        return

    del_ignore(db, conn, nick, mask)
    notice("{!r} has been unignored".format(mask))


@hook.command("listtellignores", permissions=["botcontrol", "ignore"], autohelp=False)
def list_tell_ignores(conn, nick):
    """- Returns the current list of masks who may not send you tells"""
    ignores = list(list_ignores(conn, nick))
    if not ignores:
        return "You are not ignoring tells from any users"

    return "You are ignoring tell from: {}".format(", ".join(map(repr, ignores)))
