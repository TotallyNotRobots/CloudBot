from collections import defaultdict
from datetime import datetime
from fnmatch import fnmatch
from typing import Dict, List, Set, Tuple

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    PrimaryKeyConstraint,
    String,
    Table,
    and_,
    not_,
    update,
)
from sqlalchemy.sql import select

from cloudbot import hook
from cloudbot.event import EventType
from cloudbot.hook import Priority
from cloudbot.util import database, timeformat, web
from cloudbot.util.formatting import gen_markdown_table


class TellMessage(database.Base):
    __tablename__ = "tell_messages"

    msg_id = Column(Integer, primary_key=True, autoincrement=True)
    conn = Column(String, index=True)
    sender = Column(String)
    target = Column(String, index=True)
    message = Column(String)
    is_read = Column(Boolean, default=False, index=True)
    time_sent = Column(DateTime)
    time_read = Column(DateTime)

    def format_for_message(self):
        reltime = timeformat.time_since(self.time_sent)
        return f"{self.sender} sent you a message {reltime} ago: {self.message}"

    def mark_read(self, now=None):
        if now is None:
            now = datetime.now()

        self.is_read = True
        self.time_read = now


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

disable_cache: Dict[str, Set[str]] = defaultdict(set)
ignore_cache: Dict[str, Dict[str, List[str]]] = defaultdict(
    lambda: defaultdict(list)
)
tell_cache: List[Tuple[str, str]] = []


@hook.on_start(priority=Priority.HIGHEST)
def migrate_tables(db):
    inspector = sa.inspect(db.bind)
    if not inspector.has_table("tells"):
        return

    table = sa.Table(
        "tells",
        database.metadata,
        autoload_with=db.bind,
    )

    if (
        inspector.has_table(TellMessage.__tablename__)
        and db.query(TellMessage).count() > 0
    ):
        raise Exception(
            f"Can't migrate table {table.name} to {TellMessage.__tablename__}, destination already exists"
        )

    data = [dict(row) for row in db.execute(table.select())]
    for item in data:
        item["conn"] = item.pop("connection")

    db.bulk_insert_mappings(TellMessage, data, return_defaults=True)
    db.commit()

    table.drop(db.bind)


@hook.on_start()
def load_cache(db):
    new_cache = []
    for conn, target in db.execute(
        select(
            [TellMessage.conn, TellMessage.target], not_(TellMessage.is_read)
        )
    ):
        new_cache.append((conn, target))

    tell_cache.clear()
    tell_cache.extend(new_cache)


@hook.on_start()
def load_disabled(db):
    new_cache = defaultdict(set)
    for row in db.execute(disable_table.select()):
        new_cache[row["conn"]].add(row["target"].lower())

    disable_cache.clear()
    disable_cache.update(new_cache)


@hook.on_start()
def load_ignores(db):
    new_cache = ignore_cache.copy()
    new_cache.clear()
    for row in db.execute(ignore_table.select()):
        new_cache[row["conn"].lower()][row["nick"].lower()].append(row["mask"])

    ignore_cache.clear()
    ignore_cache.update(new_cache)


def is_disable(conn, target):
    return target.lower() in disable_cache[conn.name.lower()]


def ignore_exists(conn, nick, mask):
    return mask in ignore_cache[conn.name.lower()][nick.lower()]


def can_send_to_user(conn, sender, target):
    if target.lower() in disable_cache[conn.name.lower()]:
        return False

    for mask in ignore_cache[conn.name.lower()][target.lower()]:
        if fnmatch(sender, mask):
            return False

    return True


def add_disable(db, conn, setter, target, now=None):
    if now is None:
        now = datetime.now()

    db.execute(
        disable_table.insert().values(
            conn=conn.name.lower(),
            setter=setter,
            set_at=now,
            target=target.lower(),
        )
    )
    db.commit()
    load_disabled(db)


def del_disable(db, conn, target):
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
    for row in db.execute(
        disable_table.select().where(disable_table.c.conn == conn.name.lower())
    ):
        yield (row["conn"], row["target"], row["setter"], row["set_at"].ctime())


def add_ignore(db, conn, nick, mask, now=None):
    if now is None:
        now = datetime.now()

    db.execute(
        ignore_table.insert().values(
            conn=conn.name.lower(),
            set_at=now,
            nick=nick.lower(),
            mask=mask.lower(),
        )
    )
    db.commit()
    load_ignores(db)


def del_ignore(db, conn, nick, mask):
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
    for mask in ignore_cache[conn.name.lower()][nick.lower()]:
        yield mask


def get_unread(db, server, target) -> List[TellMessage]:
    query = (
        select(TellMessage)
        .where(not_(TellMessage.is_read))
        .where(TellMessage.conn == server)
        .where(TellMessage.target == target.lower())
        .order_by(TellMessage.time_sent)
    )

    return db.execute(query).scalars().all()


def count_unread(db, server, target):
    query = (
        select(sa.func.count(TellMessage.msg_id))
        .where(TellMessage.conn == server.lower())
        .where(TellMessage.target == target.lower())
        .where(not_(TellMessage.is_read))
    )

    return db.execute(query).fetchone()[0]


def read_all_tells(db, server, target):
    query = (
        update(TellMessage)
        .where(TellMessage.conn == server.lower())
        .where(TellMessage.target == target.lower())
        .where(TellMessage.is_read.is_(False))
        .values(is_read=True)
    )
    db.execute(query)
    db.commit()
    load_cache(db)


def add_tell(db, server, sender, target, message):
    new_tell = TellMessage(
        conn=server.lower(),
        sender=sender.lower(),
        target=target.lower(),
        message=message,
        time_sent=datetime.now(),
    )
    db.add(new_tell)
    db.commit()
    load_cache(db)


def tell_check(conn, nick):
    for _conn, _target in tell_cache:
        if (conn, nick.lower()) == (_conn, _target):
            return True

    return False


@hook.event([EventType.message, EventType.action], singlethread=True)
def tellinput(conn, db, nick, notice, content):
    if "showtells" in content.lower():
        return

    if not tell_check(conn.name, nick):
        return

    tells = get_unread(db, conn.name, nick)

    if not tells:
        return

    first_tell = tells[0]
    reply = first_tell.format_for_message()

    if len(tells) > 1:
        reply += " (+{} more, {}showtells to view)".format(
            len(tells) - 1, conn.config["command_prefix"][0]
        )

    notice(reply)

    first_tell.mark_read()
    db.commit()
    load_cache(db)


@hook.command(autohelp=False)
def showtells(nick, notice, db, conn):
    """- View all pending tell messages (sent in a notice)."""

    tells = get_unread(db, conn.name, nick)

    if not tells:
        notice("You have no pending messages.")
        return

    for tell in tells:
        notice(tell.format_for_message())

    read_all_tells(db, conn.name, nick)


@hook.command("tell")
def tell_cmd(text, nick, db, conn, mask, event):
    """<nick> <message> - Relay <message> to <nick> when <nick> is around."""
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

    if (
        not event.is_nick_valid(target.lower())
        or target.lower() == conn.nick.lower()
    ):
        event.notice("Invalid nick '{}'.".format(target))
        return

    if count_unread(db, conn.name, target.lower()) >= 10:
        event.notice(
            "Sorry, {} has too many messages queued already.".format(target)
        )
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


@hook.command(
    "listtelldisabled", permissions=["botcontrol", "ignore"], autohelp=False
)
def list_tell_disabled(conn, db):
    """- Returns the current list of people who are not able to recieve tells"""
    ignores = list(list_disabled(db, conn))
    md = gen_markdown_table(
        ["Connection", "Target", "Setter", "Set At"], ignores
    )
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


@hook.command(
    "listtellignores", permissions=["botcontrol", "ignore"], autohelp=False
)
def list_tell_ignores(conn, nick):
    """- Returns the current list of masks who may not send you tells"""
    ignores = list(list_ignores(conn, nick))
    if not ignores:
        return "You are not ignoring tells from any users"

    return "You are ignoring tell from: {}".format(
        ", ".join(map(repr, ignores))
    )
