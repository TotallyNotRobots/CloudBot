import random
import re
import time

from sqlalchemy import Table, Column, String, PrimaryKeyConstraint, select

from cloudbot import hook
from cloudbot.util import database

delay = 10
floodcheck = {}

table = Table(
    'herald',
    database.metadata,
    Column('name', String),
    Column('chan', String),
    Column('quote', String),
    PrimaryKeyConstraint('name', 'chan')
)


@hook.command()
def herald(text, nick, chan, db):
    """{<message>|show|delete|remove} - adds a greeting for your nick that will be announced everytime you join the channel. Using .herald show will show your current herald and .herald delete will remove your greeting."""
    if text.lower() == "show":
        query = select([table.c.quote]).where(table.c.name == nick.lower()).where(table.c.chan == chan.lower())
        greeting = db.execute(query).fetchone()
        if greeting:
            return greeting[0]
        else:
            return "you don't have a herald set try .herald <message> to set your greeting."
    elif text.lower() in ["delete", "remove"]:
        greeting = db.execute(
            select([table.c.quote]).where(table.c.name == nick.lower()).where(table.c.chan == chan.lower())
        ).fetchone()
        query = table.delete().where(table.c.name == nick.lower()).where(table.c.chan == chan.lower())
        res = db.execute(query)
        db.commit()
        if res.rowcount > 0:
            return "greeting \'{}\' for {} has been removed".format(greeting[0], nick)
        else:
            return "no herald set, unable to delete."
    else:
        res = db.execute(
            table.update().where(table.c.name == nick.lower()).where(table.c.chan == chan.lower()).values(quote=text)
        )
        if res.rowcount == 0:
            db.execute(table.insert().values(name=nick.lower(), chan=chan.lower(), quote=text))

        db.commit()
        return "greeting successfully added"


@hook.command(permissions=["botcontrol", "snoonetstaff"])
def deleteherald(text, chan, db):
    """<nickname> - Delete [nickname]'s herald."""

    nick = text.strip()

    res = db.execute(
        table.delete().where(table.c.name == nick.lower()).where(table.c.chan == chan.lower())
    )

    db.commit()

    if res.rowcount > 0:
        return "greeting for {} has been removed".format(text.lower())
    else:
        return "{} does not have a herald".format(text.lower())


@hook.irc_raw("JOIN", singlethread=True)
def welcome(nick, message, db, bot, chan):
    decoy = re.compile('[Òo○O0öøóȯôőŏᴏōο][<>＜]')
    colors_re = re.compile("\x02|\x03(?:\d{1,2}(?:,\d{1,2})?)?", re.UNICODE)
    bino_re = re.compile('b+i+n+o+', re.IGNORECASE)
    offensive_re = re.compile('卐')

    grab = bot.plugin_manager.find_plugin("grab")

    if chan in floodcheck:
        if time.time() - floodcheck[chan] <= delay:
            return
    else:
        floodcheck[chan] = time.time()

    welcome = db.execute(
        select([table.c.quote]).where(table.c.name == nick.lower()).where(table.c.chan == chan.lower())
    ).fetchone()
    if welcome:
        greet = welcome[0]
        stripped = greet.translate(dict.fromkeys(["\u200b", " ", "\u202f", "\x02"]))
        stripped = colors_re.sub("", stripped)
        greet = re.sub(bino_re, 'flenny', greet)
        greet = re.sub(offensive_re, ' freespeech oppression ', greet)

        words = greet.lower().split()
        cmd = words.pop(0)
        if cmd == ".grabrandom":
            text = ""
            if words:
                text = random.choice(words)

            if grab is not None:
                out = grab.code.grabrandom(text, chan, message)
            else:
                out = "grab.py not loaded, original herald: {}".format(greet)

            if out:
                message(out, chan)
        elif decoy.search(stripped):
            message("DECOY DUCK --> {}".format(greet), chan)
        else:
            message("\u200b {}".format(greet), chan)
        floodcheck[chan] = time.time()
