from __future__ import annotations

import asyncio
from collections import defaultdict
from copy import copy
from threading import RLock
from typing import TYPE_CHECKING, final

from sqlalchemy import and_, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from cloudbot import hook
from cloudbot.util import database

if TYPE_CHECKING:
    from cloudbot.client import Client


@final
class Autojoin(database.Base):
    __tablename__ = "autojoin"

    conn: Mapped[str] = mapped_column(primary_key=True)
    chan: Mapped[str] = mapped_column(primary_key=True)


chan_cache: dict[str, set[str]] = defaultdict(set)
db_lock = RLock()


@hook.on_start()
def load_cache(db: Session) -> None:
    new_cache = defaultdict[str, set[str]](set)
    for row in db.query(Autojoin).all():
        new_cache[row.conn].add(row.chan)

    with db_lock:
        chan_cache.clear()
        chan_cache.update(new_cache)


@hook.irc_raw("376")
async def do_joins(conn: Client) -> None:
    while not conn.ready:
        await asyncio.sleep(1)

    join_throttle = conn.config.get("join_throttle", 0.4)
    for chan in copy(chan_cache[conn.name]):
        conn.join(chan)
        await asyncio.sleep(join_throttle)


@hook.irc_raw("JOIN", singlethread=True)
def add_chan(db: Session, conn: Client, chan: str, nick: str) -> None:
    chans = chan_cache[conn.name]
    chan = chan.casefold()
    if nick.casefold() != conn.nick.casefold() or chan in chans:
        return

    with db_lock:
        try:
            db.add(Autojoin(conn=conn.name.casefold(), chan=chan.casefold()))
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            load_cache(db)


@hook.irc_raw("PART", singlethread=True)
def on_part(db: Session, conn: Client, chan: str, nick: str) -> None:
    if nick.casefold() != conn.nick.casefold():
        return

    with db_lock:
        db.execute(
            delete(Autojoin).where(
                and_(
                    Autojoin.conn == conn.name.casefold(),
                    Autojoin.chan == chan.casefold(),
                )
            )
        )
        db.commit()

    load_cache(db)


@hook.irc_raw("KICK", singlethread=True)
def on_kick(db: Session, conn: Client, chan: str, target: str) -> None:
    on_part(db, conn, chan, target)
