import logging
import random
from collections import defaultdict
from threading import RLock

from sqlalchemy import Table, Column, String
from sqlalchemy.exc import SQLAlchemyError

from cloudbot import hook
from cloudbot.util import database
from cloudbot.util.pager import paginated_list

search_pages = defaultdict(dict)

table = Table(
    'grab',
    database.metadata,
    Column('name', String),
    Column('time', String),
    Column('quote', String),
    Column('chan', String)
)

grab_cache = {}
grab_locks = defaultdict(dict)
grab_locks_lock = RLock()
cache_lock = RLock()

logger = logging.getLogger("cloudbot")


@hook.on_start()
def load_cache(db):
    """
    :type db: sqlalchemy.orm.Session
    """
    with cache_lock:
        grab_cache.clear()
        for row in db.execute(table.select().order_by(table.c.time)):
            name = row["name"].lower()
            quote = row["quote"]
            chan = row["chan"]
            grab_cache.setdefault(chan, {}).setdefault(name, []).append(quote)


@hook.command("moregrab", autohelp=False)
def moregrab(text, chan, conn):
    """if a grab search has lots of results the results are pagintated. If the most recent search is paginated the pages are stored for retreival. If no argument is given the next page will be returned else a page number can be specified."""
    pages = search_pages[conn.name][chan]
    if not pages:
        return "There are no grabsearch pages to show."

    if text:
        try:
            index = int(text)
        except ValueError:
            return "Please specify an integer value."

        page = pages[index - 1]
        if page is None:
            return "Please specify a valid page number between 1 and {}.".format(len(pages))
        else:
            return page
    else:
        page = pages.next()
        if page is not None:
            return page
        else:
            return "All pages have been shown you can specify a page number or do a new search."


def check_grabs(name, quote, chan):
    try:
        if quote in grab_cache[chan][name]:
            return True
        else:
            return False
    except KeyError:
        return False


def grab_add(nick, time, msg, chan, db, conn):
    # Adds a quote to the grab table
    db.execute(table.insert().values(name=nick, time=time, quote=msg, chan=chan))
    db.commit()
    load_cache(db)


def get_latest_line(conn, chan, nick):
    for name, timestamp, msg in reversed(conn.history[chan]):
        if nick.casefold() == name.casefold():
            return name, timestamp, msg

    return None, None, None


@hook.command()
def grab(text, nick, chan, db, conn):
    """grab <nick> grabs the last message from the
    specified nick and adds it to the quote database"""
    if text.lower() == nick.lower():
        return "Didn't your mother teach you not to grab yourself?"

    with grab_locks_lock:
        grab_lock = grab_locks[conn.name.casefold()].setdefault(chan.casefold(), RLock())

    with grab_lock:
        name, timestamp, msg = get_latest_line(conn, chan, text)
        if not msg:
            return "I couldn't find anything from {} in recent history.".format(text)

        if check_grabs(text.casefold(), msg, chan):
            return "I already have that quote from {} in the database".format(text)

        try:
            grab_add(name.casefold(), timestamp, msg, chan, db, conn)
        except SQLAlchemyError:
            logger.exception("Error occurred when grabbing %s in %s", name, chan)
            return "Error occurred."

        if check_grabs(name.casefold(), msg, chan):
            return "the operation succeeded."
        else:
            return "the operation failed"


def format_grab(name, quote):
    # add nonbreaking space to nicks to avoid highlighting people with printed grabs
    name = "{}{}{}".format(name[0], u"\u200B", name[1:])
    if quote.startswith("\x01ACTION") or quote.startswith("*"):
        quote = quote.replace("\x01ACTION", "").replace("\x01", "")
        out = "* {}{}".format(name, quote)
        return out
    else:
        out = "<{}> {}".format(name, quote)
        return out


@hook.command("lastgrab", "lgrab")
def lastgrab(text, chan, message):
    """prints the last grabbed quote from <nick>."""
    lgrab = ""
    try:
        lgrab = grab_cache[chan][text.lower()][-1]
    except (KeyError, IndexError):
        return "<{}> has never been grabbed.".format(text)
    if lgrab:
        quote = lgrab
        message(format_grab(text, quote), chan)


@hook.command("grabrandom", "grabr", autohelp=False)
def grabrandom(text, chan, message):
    """grabs a random quote from the grab database"""
    grab = ""
    name = ""
    if text:
        tokens = text.split(' ')
        if len(tokens) > 1:
            name = random.choice(tokens)
        else:
            name = tokens[0]
    else:
        try:
            name = random.choice(list(grab_cache[chan].keys()))
        except KeyError:
            return "I couldn't find any grabs in {}.".format(chan)
    try:
        grab = random.choice(grab_cache[chan][name.lower()])
    except KeyError:
        return "it appears {} has never been grabbed in {}".format(name, chan)
    if grab:
        message(format_grab(name, grab), chan)
    else:
        return "Hmmm try grabbing a quote first."


@hook.command("grabsearch", "grabs", autohelp=False)
def grabsearch(text, chan, conn):
    """.grabsearch <text> matches "text" against nicks or grab strings in the database"""
    result = []
    try:
        quotes = grab_cache[chan][text.lower()]
        for grab in quotes:
            result.append((text, grab))
    except KeyError:
        pass
    for name in grab_cache[chan]:
        for grab in grab_cache[chan][name]:
            if name != text.lower():
                if text.lower() in grab.lower():
                    result.append((name, grab))
    if result:
        grabs = []
        for name, quote in result:
            if text.lower() == name:
                name = text
            grabs.append(format_grab(name, quote))
        pager = paginated_list(grabs)
        search_pages[conn.name][chan] = pager
        page = pager.next()
        if len(page) > 1:
            page[-1] += " .moregrab"

        return page
    else:
        return "I couldn't find any matches for {}.".format(text)
