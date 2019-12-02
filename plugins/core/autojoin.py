import asyncio
from collections import defaultdict
from copy import copy
from threading import RLock

from sqlalchemy import PrimaryKeyConstraint, Column, String, Table, and_
from sqlalchemy.exc import IntegrityError

from cloudbot import hook
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


def get_channels(db, conn):
    return db.execute(table.select().where(table.c.conn == conn.name.casefold())).fetchall()


@hook.on_start
def load_cache(db):
    new_cache = defaultdict(set)
    for row in db.execute(table.select()):
        new_cache[row['conn']].add(row['chan'])

    with db_lock:
        chan_cache.clear()
        chan_cache.update(new_cache)


@hook.irc_raw('376')
async def do_joins(conn):
    while not conn.ready:
        await asyncio.sleep(1)

    join_throttle = conn.config.get("join_throttle", 0.4)
    for chan in copy(chan_cache[conn.name]):
        conn.join(chan)
        await asyncio.sleep(join_throttle)


@hook.irc_raw('JOIN', singlethread=True)
def add_chan(db, conn, chan, nick):
    chans = chan_cache[conn.name]
    chan = chan.casefold()
    if nick.casefold() == conn.nick.casefold() and chan not in chans:
        with db_lock:
            try:
                db.execute(table.insert().values(conn=conn.name.casefold(), chan=chan.casefold()))
            except IntegrityError:
                db.rollback()
            else:
                db.commit()

                load_cache(db)


@hook.irc_raw('PART', singlethread=True)
def on_part(db, conn, chan, nick):
    if nick.casefold() == conn.nick.casefold():
        with db_lock:
            db.execute(
                table.delete().where(and_(table.c.conn == conn.name.casefold(), table.c.chan == chan.casefold())))
            db.commit()

        load_cache(db)


@hook.irc_raw('KICK', singlethread=True)
def on_kick(db, conn, chan, target):
    on_part(db, conn, chan, target)
