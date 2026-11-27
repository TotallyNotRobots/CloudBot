"""
Store and retrieve channel keys in a database table

Author:
- linuxdaemon
"""

from __future__ import annotations

from itertools import zip_longest
from typing import TYPE_CHECKING, final

import sqlalchemy as sa
from sqlalchemy import delete
from sqlalchemy.orm import Mapped, mapped_column

from cloudbot import hook
from cloudbot.client import Client
from cloudbot.util import database
from cloudbot.util.irc import parse_mode_string
from plugins.core import server_info

if TYPE_CHECKING:
    from irclib.parser import Message, ParamList
    from sqlalchemy.orm import Session

    from cloudbot.client import Client
    from cloudbot.clients.irc import IrcClient


@final
class ChannelKey(database.Base):
    __tablename__ = "channel_keys"

    conn: Mapped[str] = mapped_column(primary_key=True)
    chan: Mapped[str] = mapped_column(primary_key=True)
    key: Mapped[str | None]


@hook.on_connect(clients=["irc"])
def load_keys(conn: IrcClient, db: Session) -> None:
    """
    Load channel keys to the client
    """
    conn.clear_channel_keys()
    for row in (
        db.query(ChannelKey).filter(ChannelKey.conn == conn.name.lower()).all()
    ):
        conn.set_channel_key(row.chan, row.key)


@hook.irc_raw("MODE")
def handle_modes(
    irc_paramlist: ParamList, conn: IrcClient, db, chan: str
) -> None:
    """
    Handle mode changes
    """
    if not chan.startswith("#"):
        return

    modes = irc_paramlist[1]
    mode_params = list(irc_paramlist[2:])
    serv_info = server_info.get_server_info(conn)
    mode_changes = parse_mode_string(
        modes, mode_params, server_info.get_channel_modes(serv_info)
    )
    updated = False
    for change in mode_changes:
        if change.char == "k":
            updated = True
            if change.adding:
                set_key(db, conn, chan, change.param)
            else:
                clear_key(db, conn, chan)

    if updated:
        load_keys(conn, db)


def make_clause(conn: Client, chan: str) -> sa.ColumnElement[bool]:
    """
    Generate a WHERE clause to match keys for this conn+channel
    """
    return sa.and_(
        ChannelKey.conn == conn.name.lower(), ChannelKey.chan == chan.lower()
    )


def clear_key(db: Session, conn: Client, chan: str) -> None:
    """
    Remove a channel's key from the DB
    """
    db.execute(delete(ChannelKey).where(make_clause(conn, chan)))


def set_key(db: Session, conn: IrcClient, chan: str, key: str | None) -> None:
    """
    Set the key for a channel
    """
    db.merge(
        ChannelKey(conn=conn.name.lower(), chan=chan.lower(), key=key or None)
    )
    db.commit()

    conn.set_channel_key(chan, key)


@hook.irc_out()
def check_send_key(
    conn: IrcClient, parsed_line: Message, db: Session
) -> Message:
    """
    Parse outgoing JOIN messages and store used channel keys
    """
    if parsed_line.command == "JOIN":
        if len(parsed_line.parameters) > 1:
            keys = parsed_line.parameters[1]
        else:
            keys = ""

        for chan, key in zip_longest(
            *map(lambda s: s.split(","), (parsed_line.parameters[0], keys))
        ):
            if key:
                set_key(db, conn, chan, key)

    return parsed_line
