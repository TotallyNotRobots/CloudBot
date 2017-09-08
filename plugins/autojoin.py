import asyncio

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


def get_channels(db, conn):
    return db.execute(table.select().where(table.c.conn == conn.name.casefold())).fetchall()


@asyncio.coroutine
@hook.irc_raw('004')
def do_joins(db, conn, async):
    chans = yield from async(get_channels, db, conn)
    for chan in chans:
        conn.join(chan[1])
        yield from asyncio.sleep(0.4)


@hook.irc_raw('JOIN', singlethread=True)
def add_chan(db, conn, chan, nick):
    if nick.casefold() == conn.nick.casefold():
        try:
            db.execute(table.insert().values(conn=conn.name.casefold(), chan=chan.casefold()))
            db.commit()
        except IntegrityError:
            pass


@hook.irc_raw('PART', singlethread=True)
def on_part(db, conn, chan, nick):
    if nick.casefold() == conn.nick.casefold():
        db.execute(table.delete().where(and_(table.c.conn == conn.name.casefold(), table.c.chan == chan.casefold())))
        db.commit()


@hook.irc_raw('KICK', singlethread=True)
def on_kick(db, conn, chan, target):
    if target.casefold() == conn.nick.casefold():
        db.execute(table.delete().where(and_(table.c.conn == conn.name.casefold(), table.c.chan == chan.casefold())))
        db.commit()
