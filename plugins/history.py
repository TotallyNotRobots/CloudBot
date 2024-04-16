import asyncio
import re
import time
from collections import deque
from datetime import datetime

from sqlalchemy import (
    Column,
    Float,
    PrimaryKeyConstraint,
    String,
    Table,
    select,
)

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
    """Tracks messages for the .seen command
    :type event: cloudbot.event.Event
    :type db: sqlalchemy.orm.Session
    """
    # keep private messages private
    now = time.time()
    if event.chan[:1] == "#" and not re.findall(
        "^s/.*/.*/$", event.content.lower()
    ):
        res = db.execute(
            table.update()
            .values(time=now, quote=event.content, host=str(event.mask))
            .where(table.c.name == event.nick.lower())
            .where(table.c.chan == event.chan)
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


def track_history(event, message_time, conn):
    """
    :type event: cloudbot.event.Event
    :type conn: cloudbot.client.Client
    """
    try:
        history = conn.history[event.chan]
    except KeyError:
        conn.history[event.chan] = deque(maxlen=100)
        # what are we doing here really
        # really really
        history = conn.history[event.chan]

    data = (event.nick, message_time, event.content)
    history.append(data)


@hook.event([EventType.message, EventType.action], singlethread=True)
def chat_tracker(event, db, conn):
    """
    :type db: sqlalchemy.orm.Session
    :type event: cloudbot.event.Event
    :type conn: cloudbot.client.Client
    """
    if event.type is EventType.action:
        event.content = f"\x01ACTION {event.content}\x01"

    message_time = time.time()
    track_seen(event, db)
    track_history(event, message_time, conn)


@hook.command(autohelp=False)
@asyncio.coroutine
def resethistory(event, conn):
    """- resets chat history for the current channel
    :type event: cloudbot.event.Event
    :type conn: cloudbot.client.Client
    """
    try:
        conn.history[event.chan].clear()
        return "Reset chat history for current channel."
    except KeyError:
        # wat
        return "There is no history for this channel."


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
        select([table.c.name, table.c.time, table.c.quote])
        .where(table.c.name == text.lower())
        .where(table.c.chan == chan)
    ).fetchone()

    if last_seen:
        reltime = timeformat.time_since(last_seen[1])
        if last_seen[2][0:1] == "\x01":
            return f"{text} was last seen {reltime} ago: * {text} {last_seen[2][8:-1]}"
        else:
            return f"{text} was last seen {reltime} ago saying: {last_seen[2]}"
    else:
        return f"I've never seen {text} talking in this channel."


@hook.command("lastlink", "ll", "lasturl", autohelp=False)
def lastlink(text, chan, conn):
    """[<nick>] - gets the last link posted by a user or in the channel if no argument is supplied"""
    try:
        history = reversed(conn.history[chan])
    except KeyError:
        return "There is no history for this channel."

    pattern = ".*\\b(https?:\\/\\/)?(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)\\b.*"

    i = 0
    max_i = 50000

    for nick, message_time, message in history:
        if i > max_i:
            break
        i += 1
        if nick == text or not text:
            match = re.match(pattern, message)
            if match:
                date = datetime.fromtimestamp(message_time).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                return f"{date} {nick}: {message}"

    return "No links found" if not text else f"No links found for nick: {text}"


@hook.command("said", autohelp=False)
def searchword(text, chan, conn):
    """[<nick>] <text> - gets the last message sen't by the nick that contains the [text] string"""
    try:
        history = reversed(conn.history[chan])
    except KeyError:
        return "There is no history for this channel."

    text = text.strip()
    if not text or len(text.split()) < 2:
        return "Please provide a nick and a search string."

    search_nick = text.split()[0]
    text = text[len(search_nick) :].strip()

    i = 0
    max_i = 50000

    history.__next__()
    for nick, message_time, message in history:
        if i > max_i:
            break
        i += 1
        if nick == search_nick or not text or search_nick == "*":
            if text in message:
                date = datetime.fromtimestamp(message_time).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                message = message.replace("\x01ACTION ", "* ").replace(
                    "\x01", ""
                )
                message = message.replace(text, f"\x02{text}\x02")
                return f"{date} {nick}: {message}"

    return f"Seems like {search_nick} hasn't said anything containing '{text}' recently"


@hook.command("now", autohelp=False)
def now(text, chan, conn):
    """Returns now in local time"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@hook.command("utc", autohelp=False)
def utc(text, chan, conn):
    """Returns now in UTC"""
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
