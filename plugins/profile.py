import random
import re
import string
from collections import defaultdict
from typing import Dict

from sqlalchemy import Column, String, Table, and_

from cloudbot import hook
from cloudbot.util import database
from cloudbot.util.pager import CommandPager, paginated_list

category_re = r"[A-Za-z0-9]+"
data_re = re.compile(r"({})\s(.+)".format(category_re))

# borrowed pagination code from grab.py
cat_pages: Dict[str, Dict[str, CommandPager]] = defaultdict(dict)
confirm_keys: Dict[str, Dict[str, str]] = defaultdict(dict)

table = Table(
    "profile",
    database.metadata,
    Column("chan", String),
    Column("nick", String),
    Column("category", String),
    Column("text", String),
)

profile_cache: Dict[str, Dict[str, Dict[str, str]]] = {}


@hook.on_start()
def load_cache(db):
    new_cache = profile_cache.copy()
    new_cache.clear()
    for row in db.execute(table.select().order_by(table.c.category)):
        nick = row["nick"].lower()
        cat = row["category"]
        text = row["text"]
        chan = row["chan"]
        new_cache.setdefault(chan, {}).setdefault(nick, {})[cat] = text

    profile_cache.clear()
    profile_cache.update(new_cache)


def format_profile(nick, category, text):
    # Add zwsp to avoid pinging users
    nick = "{}{}{}".format(nick[0], "\u200B", nick[1:])
    msg = "{}->{}: {}".format(nick, category, text)
    return msg


# modified from grab.py
@hook.command("moreprofile", autohelp=False)
def moreprofile(text, chan, nick, notice):
    """[page] - If a category search has lots of results the results are paginated. If the most recent search is
    paginated the pages are stored for retrieval. If no argument is given the next page will be returned else a page
    number can be specified."""
    chan_pages = cat_pages[chan.casefold()]
    pages = chan_pages.get(nick.casefold())
    if not pages:
        notice("There are no category pages to show.")
        return

    page = pages.handle_lookup(text)
    for line in page:
        notice(line)


@hook.command()
def profile(text, chan, notice, nick):
    """<nick> [category] - Returns a user's saved profile data from \"<category>\", or lists all available profile
    categories for the user if no category specified"""
    chan_cf = chan.casefold()
    nick_cf = nick.casefold()

    # Check if we are in a PM with the user
    if nick_cf == chan_cf:
        return "Profile data not available outside of channels"

    chan_profiles = profile_cache.get(chan_cf, {})

    # Split the text in to the nick and requested category
    unpck = text.split(None, 1)
    pnick = unpck.pop(0)
    pnick_cf = pnick.casefold()
    user_profile = chan_profiles.get(pnick_cf, {})
    if not user_profile:
        notice(
            "User {} has no profile data saved in this channel".format(pnick)
        )
        return None

    # Check if the caller specified a profile category, if not, send a NOTICE with the users registered categories
    if not unpck:
        cats = list(user_profile.keys())

        pager = paginated_list(cats, ", ", pager_cls=CommandPager)
        cat_pages[chan_cf][nick_cf] = pager
        page = pager.next()
        page[0] = "Categories: {}".format(page[0])
        if len(pager) > 1:
            page[-1] += " .moreprofile"

        for line in page:
            notice(line)

        return None

    category = unpck.pop(0)
    cat_cf = category.casefold()
    if cat_cf not in user_profile:
        notice(
            "User {} has no profile data for category {} in this channel".format(
                pnick, category
            )
        )
        return None

    content = user_profile[cat_cf]
    return format_profile(pnick, category, content)


@hook.command()
def profileadd(text, chan, nick, notice, db):
    """<category> <content> - Adds data to your profile in the current channel under \"<category>\" """
    if nick.casefold() == chan.casefold():
        return "Profile data can not be set outside of channels"

    match = data_re.match(text)

    if not match:
        notice("Invalid data")
        return None

    chan_profiles = profile_cache.get(chan.casefold(), {})
    user_profile = chan_profiles.get(nick.casefold(), {})
    cat, data = match.groups()
    if cat.casefold() not in user_profile:
        db.execute(
            table.insert().values(
                chan=chan.casefold(),
                nick=nick.casefold(),
                category=cat.casefold(),
                text=data,
            )
        )
        db.commit()
        load_cache(db)
        return "Created new profile category {}".format(cat)

    db.execute(
        table.update()
        .values(text=data)
        .where(
            (
                and_(
                    table.c.nick == nick.casefold(),
                    table.c.chan == chan.casefold(),
                    table.c.category == cat.casefold(),
                )
            )
        )
    )
    db.commit()
    load_cache(db)
    return "Updated profile category {}".format(cat)


@hook.command()
def profiledel(nick, chan, text, notice, db):
    """<category> - Deletes \"<category>\" from a user's profile"""
    if nick.casefold() == chan.casefold():
        return "Profile data can not be set outside of channels"

    category = text.split()[0]

    chan_profiles = profile_cache.get(chan.casefold(), {})
    user_profile = chan_profiles.get(nick.casefold(), {})
    if category.casefold() not in user_profile:
        notice("That category does not exist in your profile")
        return None

    db.execute(
        table.delete().where(
            (
                and_(
                    table.c.nick == nick.casefold(),
                    table.c.chan == chan.casefold(),
                    table.c.category == category.casefold(),
                )
            )
        )
    )
    db.commit()
    load_cache(db)
    return "Deleted profile category {}".format(category)


@hook.command(autohelp=False)
def profileclear(nick, chan, text, notice, db):
    """[key] - Clears all of your profile data in the current channel"""
    if nick.casefold() == chan.casefold():
        return "Profile data can not be set outside of channels"

    if text:
        if (
            nick in confirm_keys[chan.casefold()]
            and text == confirm_keys[chan.casefold()][nick.casefold()]
        ):
            del confirm_keys[chan.casefold()][nick.casefold()]
            db.execute(
                table.delete().where(
                    (
                        and_(
                            table.c.nick == nick.casefold(),
                            table.c.chan == chan.casefold(),
                        )
                    )
                )
            )
            db.commit()
            load_cache(db)
            return "Profile data cleared for {}.".format(nick)

        notice("Invalid confirm key")
        return None

    key = "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(10)
    )
    confirm_keys[chan.casefold()][nick.casefold()] = key
    notice(
        'Are you sure you want to clear all of your profile data in {}? use ".profileclear {}" to confirm'.format(
            chan, key
        )
    )
    return None
