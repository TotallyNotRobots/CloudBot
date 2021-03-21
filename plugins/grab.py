import logging
import random
from collections import defaultdict
from threading import RLock
from typing import Dict, List, Tuple

from sqlalchemy import Column, String, Table
from sqlalchemy.exc import SQLAlchemyError

from cloudbot import hook
from cloudbot.util import database
from cloudbot.util.pager import CommandPager, paginated_list

search_pages: Dict[str, Dict[str, CommandPager]] = defaultdict(dict)

table = Table(
    "grab",
    database.metadata,
    Column("name", String),
    Column("time", String),
    Column("quote", String),
    Column("chan", String),
)

grab_cache: Dict[str, Dict[str, List[str]]] = {}
grab_locks: Dict[str, Dict[str, RLock]] = defaultdict(dict)
grab_locks_lock = RLock()
cache_lock = RLock()

logger = logging.getLogger("cloudbot")


@hook.on_start()
def load_cache(db):
    new_cache = grab_cache.copy()
    new_cache.clear()
    for row in db.execute(table.select().order_by(table.c.time)):
        name = row["name"].lower()
        quote = row["quote"]
        chan = row["chan"]
        new_cache.setdefault(chan, {}).setdefault(name, []).append(quote)

    with cache_lock:
        grab_cache.clear()
        grab_cache.update(new_cache)


@hook.command("moregrab", autohelp=False)
def moregrab(text, chan, conn):
    """[page] - if a grab search has lots of results the results are pagintated. If the most recent search is paginated
    the pages are stored for retreival. If no argument is given the next page will be returned else a page number can
    be specified."""
    pages = search_pages[conn.name].get(chan)
    if not pages:
        return "There are no grabsearch pages to show."

    return pages.handle_lookup(text)


def check_grabs(name, quote, chan):
    try:
        if quote in grab_cache[chan][name]:
            return True

        return False
    except KeyError:
        return False


def grab_add(nick, time, msg, chan, db):
    # Adds a quote to the grab table
    db.execute(
        table.insert().values(name=nick, time=time, quote=msg, chan=chan)
    )
    db.commit()
    load_cache(db)


def get_latest_line(conn, chan, nick):
    history = conn.history.get(chan, [])
    for name, timestamp, msg in reversed(history):
        if nick.casefold() == name.casefold():
            return name, timestamp, msg

    return None, None, None


@hook.command()
def grab(text, nick, chan, db, conn):
    """<nick> - grabs the last message from the specified nick and adds it to the quote database"""
    if text.lower() == nick.lower():
        return "Didn't your mother teach you not to grab yourself?"

    with grab_locks_lock:
        grab_lock = grab_locks[conn.name.casefold()].setdefault(
            chan.casefold(), RLock()
        )

    with grab_lock:
        name, timestamp, msg = get_latest_line(conn, chan, text)
        if not msg:
            return "I couldn't find anything from {} in recent history.".format(
                text
            )

        if check_grabs(text.casefold(), msg, chan):
            return "I already have that quote from {} in the database".format(
                text
            )

        try:
            grab_add(name.casefold(), timestamp, msg, chan, db)
        except SQLAlchemyError:
            logger.exception(
                "Error occurred when grabbing %s in %s", name, chan
            )
            return "Error occurred."

        if check_grabs(name.casefold(), msg, chan):
            return "the operation succeeded."

        return "the operation failed"


def format_grab(name, quote):
    # add nonbreaking space to nicks to avoid highlighting people with printed grabs
    name = "{}{}{}".format(name[0], "\u200B", name[1:])
    if quote.startswith("\x01ACTION") or quote.startswith("*"):
        quote = quote.replace("\x01ACTION", "").replace("\x01", "")
        out = "* {}{}".format(name, quote)
        return out

    out = "<{}> {}".format(name, quote)
    return out


@hook.command("lastgrab", "lgrab")
def lastgrab(text, chan, message):
    """<nick> - prints the last grabbed quote from <nick>."""
    try:
        with cache_lock:
            lgrab = grab_cache[chan][text.lower()][-1]
    except (KeyError, IndexError):
        return "{} has never been grabbed.".format(text)

    if lgrab:
        message(format_grab(text, lgrab), chan)

    return None


@hook.command("grabrandom", "grabr", autohelp=False)
def grabrandom(text, chan, message):
    """[nick] - grabs a random quote from the grab database"""
    with cache_lock:
        try:
            chan_grabs = grab_cache[chan]
        except KeyError:
            return "I couldn't find any grabs in {}.".format(chan)

        matching_quotes: List[Tuple[str, str]] = []

        if text:
            for nick in text.split():
                try:
                    quotes = chan_grabs[nick.lower()]
                except LookupError:
                    pass
                else:
                    matching_quotes.extend((nick, quote) for quote in quotes)
        else:
            matching_quotes.extend(
                (name, quote)
                for name, quotes in chan_grabs.items()
                for quote in quotes
            )

    if not matching_quotes:
        return "I couldn't find any grabs in {}.".format(chan)

    name, quote_text = random.choice(matching_quotes)

    message(format_grab(name, quote_text))
    return None


@hook.command("grabsearch", "grabs", autohelp=False)
def grabsearch(text, chan, conn):
    """[text] - matches "text" against nicks or grab strings in the database"""
    result: List[Tuple[str, str]] = []
    lower_text = text.lower()
    with cache_lock:
        try:
            chan_grabs = grab_cache[chan]
        except LookupError:
            return "I couldn't find any grabs in {}.".format(chan)

        try:
            quotes = chan_grabs[lower_text]
        except KeyError:
            pass
        else:
            result.extend((text, quote) for quote in quotes)

        for name, quotes in chan_grabs.items():
            if name != lower_text:
                result.extend(
                    (name, quote)
                    for quote in quotes
                    if lower_text in quote.lower()
                )

    if not result:
        return "I couldn't find any matches for {}.".format(text)

    grabs = []
    for name, quote in result:
        if lower_text == name:
            name = text

        grabs.append(format_grab(name, quote))

    pager = paginated_list(grabs, pager_cls=CommandPager)
    search_pages[conn.name][chan] = pager
    page = pager.next()
    if len(pager) > 1:
        page[-1] += " .moregrab"

    return page
