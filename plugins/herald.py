import random
import re
import time

from sqlalchemy import Table, Column, String, PrimaryKeyConstraint

from cloudbot import hook
from cloudbot.util import database

opt_out = []
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
    """herald [message] adds a greeting for your nick that will be announced everytime you join the channel. Using .herald show will show your current herald and .herald delete will remove your greeting."""
    if text.lower() == "show":
        greeting = db.execute(
            "SELECT quote FROM herald WHERE name = :name AND chan = :chan",
            {'name': nick.lower(), 'chan': chan}
        ).fetchone()
        if greeting:
            return greeting[0]
        else:
            return "you don't have a herald set try .herald <message> to set your greeting."
    elif text.lower() in ["delete", "remove"]:
        greeting = db.execute(
            "SELECT quote FROM herald WHERE name = :name AND chan = :chan",
            {'name': nick.lower(), 'chan': chan}
        ).fetchone()[0]
        db.execute("DELETE FROM herald WHERE name = :name AND chan = :chan", {'name': nick.lower(), 'chan': chan})
        db.commit()
        return ("greeting \'{}\' for {} has been removed".format(greeting, nick))
    else:
        db.execute(
            "insert or replace into herald(name, chan, quote) values(:name, :chan, :quote)",
            {'name': nick.lower(), 'chan': chan, 'quote': text}
        )
        db.commit()
        return ("greeting successfully added")


@hook.command(permissions=["botcontrol", "snoonetstaff"])
def deleteherald(text, chan, db):
    """deleteherald [nickname] Delete [nickname]'s herald."""

    tnick = db.execute(
        "SELECT name FROM herald WHERE name = :name AND chan = :chan",
        {'name': text.lower(), 'chan': chan.lower()}
    ).fetchone()

    if tnick:
        db.execute("DELETE FROM herald WHERE name = :name AND chan = :chan", {'name': text.lower(), 'chan': chan})
        db.commit()
        return "greeting for {} has been removed".format(text.lower())
    else:
        return "{} does not have a herald".format(text.lower())


@hook.irc_raw("JOIN", singlethread=True)
def welcome(nick, message, db, bot, chan):
    decoy = re.compile('[o○O0öøóóȯôőŏᴏōο](<|>|＜)')
    colors_re = re.compile("\x02|\x03(?:\d{1,2}(?:,\d{1,2})?)?", re.UNICODE)
    bino_re = re.compile('b+i+n+o+', re.IGNORECASE)
    offensive_re = re.compile('卐')

    grab = bot.plugin_manager.find_plugin("grab")

    if chan in opt_out:
        return

    if chan in floodcheck:
        if time.time() - floodcheck[chan] <= delay:
            return
    else:
        floodcheck[chan] = time.time()

    welcome = db.execute(
        "SELECT quote FROM herald WHERE name = :name AND chan = :chan",
        {'name': nick.lower(), 'chan': chan.lower()}
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
