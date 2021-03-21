import datetime
import random
import re
from collections import defaultdict
from typing import Dict

from sqlalchemy import Column, PrimaryKeyConstraint, String, Table

from cloudbot import hook
from cloudbot.util import database

table = Table(
    "herald",
    database.metadata,
    Column("name", String),
    Column("chan", String),
    Column("quote", String),
    PrimaryKeyConstraint("name", "chan"),
)


class ChannelData:
    def __init__(
        self,
        chan_interval=datetime.timedelta(seconds=10),
        user_interval=datetime.timedelta(minutes=5),
    ):
        self.user_interval = user_interval
        self.chan_interval = chan_interval
        self.next_send = datetime.datetime.min
        self.user_times = defaultdict(lambda: datetime.datetime.min)

    def can_send(self, nick: str, join_time: datetime.datetime) -> bool:
        if join_time < self.next_send:
            return False

        nick_lower = nick.lower()
        if join_time < self.user_times[nick_lower]:
            return False

        self.user_times[nick_lower] = join_time + self.user_interval
        self.next_send = join_time + self.chan_interval
        return True


user_join: Dict[str, Dict[str, ChannelData]] = defaultdict(
    lambda: defaultdict(ChannelData)
)
herald_cache: Dict[str, Dict[str, str]] = defaultdict(dict)


@hook.on_start()
def load_cache(db):
    new_cache = herald_cache.copy()
    new_cache.clear()
    for row in db.execute(table.select()):
        new_cache[row["chan"]][row["name"]] = row["quote"]

    herald_cache.clear()
    herald_cache.update(new_cache)


@hook.command()
def herald(text, nick, chan, db, reply):
    """{<message>|show|delete|remove} - adds a greeting for your nick that will be announced everytime you join the
    channel. Using .herald show will show your current herald and .herald delete will remove your greeting."""
    if text.lower() == "show":
        greeting = herald_cache[chan.casefold()].get(nick.casefold())
        if greeting is None:
            return "you don't have a herald set try .herald <message> to set your greeting."

        return greeting

    if text.lower() in ["delete", "remove"]:
        greeting = herald_cache[chan.casefold()].get(nick.casefold())
        if greeting is None:
            return "no herald set, unable to delete."

        query = (
            table.delete()
            .where(table.c.name == nick.lower())
            .where(table.c.chan == chan.lower())
        )
        db.execute(query)
        db.commit()

        reply("greeting '{}' for {} has been removed".format(greeting, nick))

        load_cache(db)
        return None

    res = db.execute(
        table.update()
        .where(table.c.name == nick.lower())
        .where(table.c.chan == chan.lower())
        .values(quote=text)
    )
    if res.rowcount == 0:
        db.execute(
            table.insert().values(
                name=nick.lower(), chan=chan.lower(), quote=text
            )
        )

    db.commit()
    reply("greeting successfully added")

    load_cache(db)

    return None


@hook.command(
    permissions=["botcontrol", "snoonetstaff", "deleteherald", "chanop"]
)
def deleteherald(text, chan, db, reply):
    """<nickname> - Delete [nickname]'s herald."""

    nick = text.strip()

    res = db.execute(
        table.delete()
        .where(table.c.name == nick.lower())
        .where(table.c.chan == chan.lower())
    )

    db.commit()

    if res.rowcount > 0:
        reply("greeting for {} has been removed".format(text.lower()))
    else:
        reply("{} does not have a herald".format(text.lower()))

    load_cache(db)


def should_send(conn, chan, nick, join_time) -> bool:
    chan_data = user_join[conn.lower()][chan.lower()]
    return chan_data.can_send(nick, join_time)


@hook.irc_raw("JOIN", singlethread=True)
def welcome(nick, message, bot, chan, conn):
    decoy = re.compile("[Òo○O0öøóȯôőŏᴏōο][<>＜]")
    colors_re = re.compile(r"\x02|\x03(?:\d{1,2}(?:,\d{1,2})?)?", re.UNICODE)
    bino_re = re.compile("b+i+n+o+", re.IGNORECASE)
    offensive_re = re.compile("卐")

    grab = bot.plugin_manager.find_plugin("grab")

    greet = herald_cache[chan.casefold()].get(nick.casefold())
    if not greet:
        return

    if not should_send(conn.name, chan, nick, datetime.datetime.now()):
        return

    stripped = greet.translate(
        dict.fromkeys(map(ord, ["\u200b", " ", "\u202f", "\x02"]))
    )
    stripped = colors_re.sub("", stripped)
    greet = re.sub(bino_re, "flenny", greet)
    greet = re.sub(offensive_re, " freespeech oppression ", greet)

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
