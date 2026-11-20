from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from fnmatch import fnmatch
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import (
    Column,
    DateTime,
    PrimaryKeyConstraint,
    String,
    Table,
    and_,
    not_,
    update,
)
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.sql import select

from cloudbot import hook
from cloudbot.event import EventType
from cloudbot.util import database, timeformat, web
from cloudbot.util.formatting import gen_markdown_table

if TYPE_CHECKING:
    from collections.abc import Iterable

    from cloudbot.client import Client
    from cloudbot.event_functions import EventNotice


class TellMessage(database.Base):
    __tablename__ = "tell_messages"

    msg_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, init=False
    )
    conn: Mapped[str | None] = mapped_column(index=True)
    sender: Mapped[str | None]
    target: Mapped[str | None] = mapped_column(index=True)
    message: Mapped[str | None]
    is_read: Mapped[bool] = mapped_column(default=False, index=True)
    time_sent: Mapped[datetime | None] = mapped_column(default=None)
    time_read: Mapped[datetime | None] = mapped_column(default=None)

    def format_for_message(self) -> str:
        reltime = timeformat.time_since(self.time_sent)
        return f"{self.sender} sent you a message {reltime} ago: {self.message}"

    def mark_read(self, now=None) -> None:
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

disable_cache: dict[str, set[str]] = defaultdict(set)
ignore_cache: dict[str, dict[str, list[str]]] = defaultdict(
    lambda: defaultdict(list)
)
tell_cache: list[tuple[str, str]] = []


@hook.on_start()
def load_cache(db) -> None:
    new_cache = []
    for conn, target in db.execute(
        select(TellMessage.conn, TellMessage.target).where(
            not_(TellMessage.is_read)
        )
    ):
        new_cache.append((conn, target))

    tell_cache.clear()
    tell_cache.extend(new_cache)


@hook.on_start()
def load_disabled(db) -> None:
    new_cache = defaultdict(set)
    for row in db.execute(disable_table.select()):
        new_cache[row.conn].add(row.target.lower())

    disable_cache.clear()
    disable_cache.update(new_cache)


@hook.on_start()
def load_ignores(db) -> None:
    new_cache = ignore_cache.copy()
    new_cache.clear()
    for row in db.execute(ignore_table.select()):
        new_cache[row.conn.lower()][row.nick.lower()].append(row.mask)

    ignore_cache.clear()
    ignore_cache.update(new_cache)


def is_disable(conn: Client, target) -> bool:
    return target.lower() in disable_cache[conn.name.lower()]


def ignore_exists(conn: Client, nick, mask) -> bool:
    return mask in ignore_cache[conn.name.lower()][nick.lower()]


def can_send_to_user(conn: Client, sender, target) -> bool:
    if target.lower() in disable_cache[conn.name.lower()]:
        return False

    for mask in ignore_cache[conn.name.lower()][target.lower()]:
        if fnmatch(sender, mask):
            return False

    return True


def add_disable(db, conn: Client, setter, target, now=None) -> None:
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


def del_disable(db, conn: Client, target) -> None:
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


def list_disabled(db, conn: Client):
    for row in db.execute(
        disable_table.select().where(disable_table.c.conn == conn.name.lower())
    ):
        yield (row.conn, row.target, row.setter, row.set_at.ctime())


def add_ignore(db, conn: Client, nick, mask, now=None) -> None:
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


def del_ignore(db, conn: Client, nick, mask) -> None:
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


def list_ignores(conn: Client, nick: str) -> Iterable[str]:
    yield from ignore_cache[conn.name.lower()][nick.lower()]


def get_unread(db, server, target) -> list[TellMessage]:
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


def read_all_tells(db, server, target) -> None:
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


def add_tell(
    db: Session, server: str, sender: str, target: str, message: str
) -> None:
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


def tell_check(conn: str, nick: str) -> bool:
    for _conn, _target in tell_cache:
        if (conn, nick.lower()) == (_conn, _target):
            return True

    return False


@hook.event([EventType.message, EventType.action], singlethread=True)
def tellinput(conn: Client, db, nick, notice: EventNotice, content) -> None:
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
        reply += f" (+{len(tells) - 1} more, {conn.config['command_prefix'][0]}showtells to view)"

    notice(reply)

    first_tell.mark_read()
    db.commit()
    load_cache(db)


@hook.command(autohelp=False)
def showtells(nick, notice: EventNotice, db, conn: Client) -> None:
    """- View all pending tell messages (sent in a notice)."""

    tells = get_unread(db, conn.name, nick)

    if not tells:
        notice("You have no pending messages.")
        return

    for tell in tells:
        notice(tell.format_for_message())

    read_all_tells(db, conn.name, nick)


@hook.command("tell")
def tell_cmd(text, nick, db, conn: Client, mask, event) -> None:
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
        event.notice(f"Invalid nick '{target}'.")
        return

    if count_unread(db, conn.name, target.lower()) >= 10:
        event.notice(f"Sorry, {target} has too many messages queued already.")
        return

    add_tell(db, conn.name, sender, target.lower(), message)
    event.notice(
        f"Your message has been saved, and {target} will be notified once they are active."
    )


def check_permissions(event, *perms):
    return any(event.has_permission(perm) for perm in perms)


@hook.command("telldisable", autohelp=False)
def tell_disable(conn: Client, db, text, nick, event):
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
        return f"Tells are already disabled for {('you' if is_self else f'{target!r}')}."

    add_disable(db, conn, nick, target)
    return (
        f"Tells are now disabled for {('you' if is_self else f'{target!r}')}."
    )


@hook.command("tellenable", autohelp=False)
def tell_enable(conn: Client, db, text, event, nick):
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
        return f"Tells are already enabled for {('you' if is_self else f'{target!r}')}."

    del_disable(db, conn, target)
    return f"Tells are now enabled for {('you' if is_self else f'{target!r}')}."


@hook.command(
    "listtelldisabled", permissions=["botcontrol", "ignore"], autohelp=False
)
def list_tell_disabled(conn: Client, db):
    """- Returns the current list of people who are not able to receive tells"""
    ignores = list(list_disabled(db, conn))
    md = gen_markdown_table(
        ["Connection", "Target", "Setter", "Set At"], ignores
    )
    return web.paste(md, "md", "hastebin")


@hook.command("tellignore")
def tell_ignore(db, conn: Client, nick, text, notice: EventNotice) -> None:
    """<mask> - Disallow users matching <mask> from sending you tells"""
    mask = text.split()[0].lower()
    if ignore_exists(conn, nick, mask):
        notice(f"You are already ignoring tells from {mask!r}")
        return

    add_ignore(db, conn, nick, mask)
    notice(f"You are now ignoring tells from {mask!r}")


@hook.command("tellunignore")
def tell_unignore(db, conn: Client, nick, text, notice: EventNotice) -> None:
    """<mask> - Remove a tell ignore"""
    mask = text.split()[0].lower()
    if not ignore_exists(conn, nick, mask):
        notice(f"No ignore matching {mask!r} exists.")
        return

    del_ignore(db, conn, nick, mask)
    notice(f"{mask!r} has been unignored")


@hook.command(
    "listtellignores", permissions=["botcontrol", "ignore"], autohelp=False
)
def list_tell_ignores(conn: Client, nick) -> str:
    """- Returns the current list of masks who may not send you tells"""
    ignores = list(list_ignores(conn, nick))
    if not ignores:
        return "You are not ignoring tells from any users"

    return f"You are ignoring tell from: {', '.join(map(repr, ignores))}"
