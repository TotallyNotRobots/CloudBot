from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, final

from irclib.util.compare import match_mask
from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from cloudbot import hook
from cloudbot.util import database, web

if TYPE_CHECKING:
    from cloudbot.client import Client
    from cloudbot.event_functions import EventAdminLog, EventNotice


@final
class Ignored(database.Base):
    __tablename__ = "ignored"

    connection: Mapped[str] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(primary_key=True)
    mask: Mapped[str] = mapped_column(primary_key=True)


ignore_cache: list[tuple[str, str, str]] = []


@hook.on_start()
def load_cache(db: Session) -> None:
    new_cache = []
    for row in db.query(Ignored).all():
        conn = row.connection
        chan = row.channel
        mask = row.mask
        new_cache.append((conn, chan, mask))

    ignore_cache.clear()
    ignore_cache.extend(new_cache)


def find_ignore(conn: str, chan, mask):
    search = (conn.casefold(), chan.casefold(), mask.casefold())
    for _conn, _chan, _mask in ignore_cache:
        if search == (_conn.casefold(), _chan.casefold(), _mask.casefold()):
            return _conn, _chan, _mask

    return None


def ignore_in_cache(conn: str, chan, mask) -> bool:
    if find_ignore(conn, chan, mask):
        return True

    return False


def add_ignore(db: Session, conn: str, chan: str, mask: str) -> None:
    if ignore_in_cache(conn, chan, mask):
        return

    db.add(Ignored(connection=conn, channel=chan, mask=mask))
    db.commit()
    load_cache(db)


def remove_ignore(db, conn: str, chan, mask) -> bool:
    item = find_ignore(conn, chan, mask)
    if not item:
        return False

    conn, chan, mask = item
    clause = and_(
        Ignored.connection == conn,
        Ignored.channel == chan,
        Ignored.mask == mask,
    )
    db.execute(delete(Ignored).where(clause))
    db.commit()
    load_cache(db)

    return True


def is_ignored(conn: str, chan, mask) -> bool:
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


@hook.sieve(priority=50)
async def ignore_sieve(bot, event, _hook):  # pyright: ignore[reportUnusedParameter]  # noqa: ARG001
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


def get_user(conn: Client, text: str) -> str:
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
def ignore(
    text,
    db,
    chan,
    conn: Client,
    notice: EventNotice,
    admin_log: EventAdminLog,
    nick,
) -> None:
    """<nick|mask> - ignores all input from <nick|mask> in this channel."""
    target = get_user(conn, text)

    if ignore_in_cache(conn.name, chan, target):
        notice(f"{target} is already ignored in {chan}.")
    else:
        admin_log(f"{nick} used IGNORE to make me ignore {target} in {chan}")
        notice(f"{target} has been ignored in {chan}.")
        add_ignore(db, conn.name, chan, target)


@hook.command(permissions=["ignore", "chanop"])
def unignore(
    text,
    db,
    chan,
    conn: Client,
    notice: EventNotice,
    nick,
    admin_log: EventAdminLog,
) -> None:
    """<nick|mask> - un-ignores all input from <nick|mask> in this channel."""
    target = get_user(conn, text)

    if remove_ignore(db, conn.name, chan, target):
        admin_log(
            f"{nick} used UNIGNORE to make me stop ignoring {target} in {chan}"
        )
        notice(f"{target} has been un-ignored in {chan}.")
    else:
        notice(f"{target} is not ignored in {chan}.")


@hook.command(permissions=["ignore", "chanop"], autohelp=False)
def listignores(db, conn: Client, chan):
    """- List all active ignores for the current channel"""

    rows = db.execute(
        select(Ignored.mask).where(
            and_(
                Ignored.connection == conn.name.lower(),
                Ignored.channel == chan.lower(),
            )
        )
    ).fetchall()

    lines = "\n".join(row.mask for row in rows)
    out = f"{lines}\n"

    return web.paste(out)


@hook.command(permissions=["botcontrol"])
def global_ignore(
    text, db, conn: Client, notice: EventNotice, nick, admin_log: EventAdminLog
) -> None:
    """<nick|mask> - ignores all input from <nick|mask> in ALL channels."""
    target = get_user(conn, text)

    if ignore_in_cache(conn.name, "*", target):
        notice(f"{target} is already globally ignored.")
    else:
        notice(f"{target} has been globally ignored.")
        admin_log(
            f"{nick} used GLOBAL_IGNORE to make me ignore {target} everywhere"
        )
        add_ignore(db, conn.name, "*", target)


@hook.command(permissions=["botcontrol"])
def global_unignore(
    text, db, conn: Client, notice: EventNotice, nick, admin_log: EventAdminLog
) -> None:
    """<nick|mask> - un-ignores all input from <nick|mask> in ALL channels."""
    target = get_user(conn, text)

    if not ignore_in_cache(conn.name, "*", target):
        notice(f"{target} is not globally ignored.")
    else:
        notice(f"{target} has been globally un-ignored.")
        admin_log(
            f"{nick} used GLOBAL_UNIGNORE to make me stop ignoring {target} everywhere"
        )
        remove_ignore(db, conn.name, "*", target)


@hook.command(permissions=["botcontrol", "snoonetstaff"], autohelp=False)
def list_global_ignores(db, conn: Client):
    """- List all global ignores for the current network"""
    return listignores(db, conn, "*")


@hook.command(permissions=["botcontrol", "snoonetstaff"], autohelp=False)
def list_all_ignores(db, conn: Client, text):
    """<chan> - List all ignores for <chan>, requires elevated permissions"""
    whereclause = Ignored.connection == conn.name.lower()

    if text:
        whereclause = and_(whereclause, Ignored.channel == text.lower())

    rows = db.execute(
        select(Ignored.channel, Ignored.mask).where(whereclause)
    ).fetchall()

    ignores: dict[str, list[str]] = OrderedDict()

    for row in rows:
        ignores.setdefault(row.channel, []).append(row.mask)

    out = ""
    for chan, masks in ignores.items():
        out += f"Ignores for {chan}:\n"
        for mask in masks:
            out += f"- {mask}\n"

        out += "\n"

    return web.paste(out)
