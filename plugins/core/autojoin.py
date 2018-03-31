import asyncio
from collections import defaultdict
from threading import RLock

from sqlalchemy import PrimaryKeyConstraint, Column, String, Table, and_
from sqlalchemy.exc import IntegrityError

from cloudbot import hook
from cloudbot.event import EventType
from cloudbot.util import database

table = Table(
    'autojoin',
    database.metadata,
    Column('conn', String),
    Column('chan', String),
    PrimaryKeyConstraint('conn', 'chan')
)

chan_cache = defaultdict(set)
db_lock = RLock()


@hook.on_start
def load_cache(event):
    """
    :type event: cloudbot.event.Event
    """
    with db_lock, event.db_session() as db:
        chan_cache.clear()
        for row in db.execute(table.select()):
            chan_cache[row['conn']].add(row['chan'])


@hook.irc_raw('376')
@asyncio.coroutine
def do_joins(conn):
    join_throttle = conn.config.get("join_throttle", 0.4)
    for chan in chan_cache[conn.name]:
        conn.join(chan)
        yield from asyncio.sleep(join_throttle)


@hook.event(EventType.join, singlethread=True)
def add_chan(event, conn, chan, nick):
    chans = chan_cache[conn.name]
    chan = chan.casefold()
    if nick.casefold() == conn.nick.casefold() and chan not in chans:
        with db_lock, event.db_session() as db:
            try:
                db.execute(table.insert().values(conn=conn.name.casefold(), chan=chan.casefold()))
            except IntegrityError:
                db.rollback()
            else:
                db.commit()

        load_cache(event)


@hook.event(EventType.part, singlethread=True)
def on_part(event, conn, chan, nick):
    """
    :type event: cloudbot.event.Event
    """
    if nick.casefold() == conn.nick.casefold():
        with db_lock, event.db_session() as db:
            db.execute(
                table.delete().where(and_(
                    table.c.conn == conn.name.casefold(),
                    table.c.chan == chan.casefold()
                ))
            )
            db.commit()

        load_cache(event)


@hook.irc_raw('KICK', singlethread=True)
def on_kick(event, conn, chan, target):
    on_part(event, conn, chan, target)
