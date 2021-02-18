import random
import re
import time

from sqlalchemy import (
    Boolean,
    Column,
    PrimaryKeyConstraint,
    String,
    Table,
    not_,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.types import REAL

from cloudbot import hook
from cloudbot.util import database

qtable = Table(
    "new_quote",
    database.metadata,
    Column("chan", String),
    Column("nick", String),
    Column("add_nick", String),
    Column("msg", String),
    Column("time", REAL),
    Column("deleted", Boolean, default=False),
    PrimaryKeyConstraint("chan", "nick", "msg"),
)


@hook.on_start()
def migrate_table(db, logger):
    old_table = Table(
        "quote",
        database.metadata,
        Column("chan", String(25)),
        Column("nick", String(25)),
        Column("add_nick", String(25)),
        Column("msg", String(500)),
        Column("time", REAL),
        Column("deleted", String(5), default=0),
        PrimaryKeyConstraint("chan", "nick", "time"),
    )

    if not old_table.exists():
        database.metadata.remove(old_table)
        return

    old_quotes = db.execute(old_table.select()).fetchall()

    if not old_quotes:
        return

    logger.info("Migrating quotes table")
    qtable.drop(checkfirst=True)
    qtable.create(checkfirst=True)

    db.execute(
        qtable.insert().values(
            [
                {
                    "chan": row["chan"],
                    "nick": row["nick"],
                    "add_nick": row["add_nick"],
                    "msg": row["msg"],
                    "time": row["time"],
                    "deleted": row["deleted"] in (1, "1", True),
                }
                for row in old_quotes
            ]
        )
    )

    logger.info("Migrated all quotes")

    db.commit()
    old_table.drop()
    database.metadata.remove(old_table)


def format_quote(q, num, n_quotes):
    """Returns a formatted string of a quote"""
    _, nick, msg = q
    return "[{}/{}] <{}\u200B{}> {}".format(
        num, n_quotes, nick[:1], nick[1:], msg
    )


def add_quote(db, chan, target, sender, message):
    """Adds a quote to a nick, returns message string"""
    try:
        query = qtable.insert().values(
            chan=chan,
            nick=target.lower(),
            add_nick=sender.lower(),
            msg=message,
            time=time.time(),
        )
        db.execute(query)
        db.commit()
    except IntegrityError:
        return "Message already stored, doing nothing."
    return "Quote added."


def del_quote(db, nick, msg):
    """Deletes a quote from a nick"""
    query = (
        qtable.update()
        .where(qtable.c.chan == 1)
        .where(qtable.c.nick == nick.lower())
        .where(qtable.c.msg == msg)
        .values(deleted=True)
    )
    db.execute(query)
    db.commit()


def get_quote_num(num, count, name):
    """Returns the quote number to fetch from the DB"""
    if num:  # Make sure num is a number if it isn't false
        num = int(num)
    if count == 0:  # Error on no quotes
        raise Exception("No quotes found for {}.".format(name))
    if num and num < 0:  # Count back if possible
        num = count + num + 1 if num + count > -1 else count + 1
    if num and num > count:  # If there are not enough quotes, raise an error
        raise Exception(
            "I only have {} quote{} for {}.".format(
                count, ("s", "")[count == 1], name
            )
        )
    if num and num == 0:  # If the number is zero, set it to one
        num = 1
    if not num:  # If a number is not given, select a random one
        num = random.randint(1, count)
    return num


def get_quote_by_nick(db, nick, num=False):
    """Returns a formatted quote from a nick, random or selected by number"""

    count_query = (
        select([qtable])
        .where(not_(qtable.c.deleted))
        .where(qtable.c.nick == nick.lower())
        .alias("count")
        .count()
    )
    count = db.execute(count_query).fetchall()[0][0]

    try:
        num = get_quote_num(num, count, nick)
    except Exception as error_message:
        return error_message

    query = (
        select([qtable.c.time, qtable.c.nick, qtable.c.msg])
        .where(not_(qtable.c.deleted))
        .where(qtable.c.nick == nick.lower())
        .order_by(qtable.c.time)
        .limit(1)
        .offset((num - 1))
    )
    data = db.execute(query).fetchall()[0]
    return format_quote(data, num, count)


def get_quote_by_nick_chan(db, chan, nick, num=False):
    """Returns a formatted quote from a nick in a channel, random or selected by number"""
    count_query = (
        select([qtable])
        .where(not_(qtable.c.deleted))
        .where(qtable.c.chan == chan)
        .where(qtable.c.nick == nick.lower())
        .alias("count")
        .count()
    )
    count = db.execute(count_query).fetchall()[0][0]

    try:
        num = get_quote_num(num, count, nick)
    except Exception as error_message:
        return error_message

    query = (
        select([qtable.c.time, qtable.c.nick, qtable.c.msg])
        .where(not_(qtable.c.deleted))
        .where(qtable.c.chan == chan)
        .where(qtable.c.nick == nick.lower())
        .order_by(qtable.c.time)
        .limit(1)
        .offset((num - 1))
    )
    data = db.execute(query).fetchall()[0]
    return format_quote(data, num, count)


def get_quote_by_chan(db, chan, num=False):
    """Returns a formatted quote from a channel, random or selected by number"""
    count_query = (
        select([qtable])
        .where(not_(qtable.c.deleted))
        .where(qtable.c.chan == chan)
        .alias("count")
        .count()
    )
    count = db.execute(count_query).fetchall()[0][0]

    try:
        num = get_quote_num(num, count, chan)
    except Exception as error_message:
        return error_message

    query = (
        select([qtable.c.time, qtable.c.nick, qtable.c.msg])
        .where(not_(qtable.c.deleted))
        .where(qtable.c.chan == chan)
        .order_by(qtable.c.time)
        .limit(1)
        .offset((num - 1))
    )
    data = db.execute(query).fetchall()[0]
    return format_quote(data, num, count)


@hook.command("q", "quote")
def quote(text, nick, chan, db, notice, event):
    """[#chan] [nick] [#n] OR add <nick> <message> - gets the [#n]th quote by <nick> (defaulting to random)
    OR adds <message> as a quote for <nick> in the caller's channel"""

    add = re.match(r"add[^\w@]+(\S+?)>?\s+(.*)", text, re.I)
    retrieve = re.match(r"(\S+)(?:\s+#?(-?\d+))?$", text)
    retrieve_chan = re.match(r"(#\S+)\s+(\S+)(?:\s+#?(-?\d+))?$", text)

    if add:
        quoted_nick, msg = add.groups()
        notice(add_quote(db, chan, quoted_nick, nick, msg))
        return

    if retrieve:
        selected, num = retrieve.groups()
        by_chan = True if selected.startswith("#") else False
        if by_chan:
            return get_quote_by_chan(db, selected, num)

        return get_quote_by_nick(db, selected, num)

    if retrieve_chan:
        chan, nick, num = retrieve_chan.groups()
        return get_quote_by_nick_chan(db, chan, nick, num)

    event.notice_doc()
