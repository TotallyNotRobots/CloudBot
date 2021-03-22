"""
Store and retrieve channel keys in a database table

Author:
- linuxdaemon
"""
from itertools import zip_longest
from typing import Any, Dict, List, Optional

from irclib.parser import Message
from sqlalchemy import Column, PrimaryKeyConstraint, String, Table, and_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import BooleanClauseList, ClauseElement

from cloudbot import hook
from cloudbot.client import Client
from cloudbot.clients.irc import IrcClient
from cloudbot.util import database
from cloudbot.util.irc import parse_mode_string
from plugins.core import server_info

table = Table(
    "channel_keys",
    database.metadata,
    Column("conn", String),
    Column("chan", String),
    Column("key", String),
    PrimaryKeyConstraint("conn", "chan"),
)


@hook.connect(clients=["irc"])
def load_keys(conn: IrcClient, db) -> None:
    """
    Load channel keys to the client
    """
    query = select(
        [table.c.chan, table.c.key], table.c.conn == conn.name.lower()
    )
    conn.clear_channel_keys()
    for row in db.execute(query):
        conn.set_channel_key(row["chan"], row["key"])


@hook.irc_raw("MODE")
def handle_modes(
    irc_paramlist: List[str], conn: IrcClient, db, chan: str
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


def insert_or_update(
    db: Session, tbl: Table, data: Dict[str, Any], query: ClauseElement
) -> None:
    """
    Insert a new row or update an existing matching row
    """
    result = db.execute(tbl.update().where(query).values(**data))
    if not result.rowcount:
        db.execute(tbl.insert().values(**data))

    db.commit()


def make_clause(conn: Client, chan: str) -> BooleanClauseList:
    """
    Generate a WHERE clause to match keys for this conn+channel
    """
    return and_(
        table.c.conn == conn.name.lower(),
        table.c.chan == chan.lower(),
    )


def clear_key(db: Session, conn, chan: str) -> None:
    """
    Remove a channel's key from the DB
    """
    db.execute(table.delete().where(make_clause(conn, chan)))


def set_key(
    db: Session, conn: IrcClient, chan: str, key: Optional[str]
) -> None:
    """
    Set the key for a channel
    """
    insert_or_update(
        db,
        table,
        {"conn": conn.name.lower(), "chan": chan.lower(), "key": key or None},
        make_clause(conn, chan),
    )
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
