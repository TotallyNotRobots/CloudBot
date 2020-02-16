import re
import time

from sqlalchemy import Column, Float, PrimaryKeyConstraint, String, Table, and_, select

from cloudbot import hook
from cloudbot.event import EventType
from cloudbot.util import database, timeformat

table = Table(
    "seen_user",
    database.metadata,
    Column("name", String),
    Column("time", Float),
    Column("quote", String),
    Column("chan", String),
    Column("host", String),
    PrimaryKeyConstraint("name", "chan"),
)


def track_seen(event, db):
    """ Tracks messages for the .seen command
    :type event: cloudbot.event.Event
    :type db: sqlalchemy.orm.Session
    """
    # keep private messages private
    now = time.time()
    if event.chan[:1] == "#" and not re.findall("^s/.*/.*/$", event.content.lower()):
        res = db.execute(
            table.update()
            .where(and_(table.c.name == event.nick.lower(), table.c.chan == event.chan))
            .values(time=now, quote=event.content, host=str(event.mask))
        )
        if res.rowcount == 0:
            db.execute(
                table.insert().values(
                    name=event.nick.lower(),
                    time=now,
                    quote=event.content,
                    chan=event.chan,
                    host=str(event.mask),
                )
            )

        db.commit()


@hook.event([EventType.message, EventType.action], singlethread=True)
def chat_tracker(event, db):
    """
    :type db: sqlalchemy.orm.Session
    :type event: cloudbot.event.Event
    """
    if event.type is EventType.action:
        event.content = "\x01ACTION {}\x01".format(event.content)

    track_seen(event, db)


@hook.command()
def seen(text, nick, chan, db, event, is_nick_valid):
    """<nick> <channel> - tells when a nickname was last in active in one of my channels

    :type db: sqlalchemy.orm.Session
    :type event: cloudbot.event.Event
    """

    if event.conn.nick.lower() == text.lower():
        return "You need to get your eyes checked."

    if text.lower() == nick.lower():
        return "Have you looked in a mirror lately?"

    if not is_nick_valid(text):
        return "I can't look up that name, its impossible to use!"

    last_seen = db.execute(
        select([table.c.name, table.c.time, table.c.quote]).where(
            and_(table.c.name == text.lower(), table.c.chan == chan)
        )
    ).fetchone()

    if last_seen:
        reltime = timeformat.time_since(last_seen[1])
        if last_seen[2][0:1] == "\x01":
            return "{} was last seen {} ago: * {} {}".format(
                text, reltime, text, last_seen[2][8:-1]
            )

        return "{} was last seen {} ago saying: {}".format(text, reltime, last_seen[2])

    return "I've never seen {} talking in this channel.".format(text)
