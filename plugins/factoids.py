import re
import string
from collections import defaultdict
from typing import Dict, List

from sqlalchemy import Column, PrimaryKeyConstraint, String, Table, and_

from cloudbot import hook
from cloudbot.util import colors, database, web
from cloudbot.util.formatting import gen_markdown_table, get_text_list
from cloudbot.util.web import NoPasteException

# below is the default factoid in every channel you can modify it however you like
default_dict = {"commands": "https://snoonet.org/gonzobot"}
factoid_cache: Dict[str, Dict[str, str]] = defaultdict(default_dict.copy)

FACTOID_CHAR = "?"  # TODO: config

table = Table(
    "factoids",
    database.metadata,
    Column("word", String),
    Column("data", String),
    Column("nick", String),
    Column("chan", String),
    PrimaryKeyConstraint("word", "chan"),
)


@hook.on_start()
def load_cache(db):
    new_cache = factoid_cache.copy()
    new_cache.clear()
    for row in db.execute(table.select()):
        # assign variables
        chan = row["chan"]
        word = row["word"]
        data = row["data"]
        new_cache[chan][word] = data

    factoid_cache.clear()
    factoid_cache.update(new_cache)


def add_factoid(db, word, chan, data, nick):
    if word in factoid_cache[chan]:
        # if we have a set value, update
        db.execute(
            table.update()
            .values(data=data, nick=nick, chan=chan)
            .where(table.c.chan == chan)
            .where(table.c.word == word)
        )
        db.commit()
    else:
        # otherwise, insert
        db.execute(
            table.insert().values(word=word, data=data, nick=nick, chan=chan)
        )
        db.commit()
    load_cache(db)


def del_factoid(db, chan, word=None):
    clause = table.c.chan == chan

    if word is not None:
        clause = and_(clause, table.c.word.in_(word))

    db.execute(table.delete().where(clause))
    db.commit()
    load_cache(db)


@hook.command("r", "remember", permissions=["op", "chanop"])
def remember(text, nick, db, chan, notice, event):
    """<word> [+]<data> - remembers <data> with <word> - add + to <data> to append. If the input starts with <act> the
    message will be sent as an action. If <user> in in the message it will be replaced by input arguments when command
    is called."""
    try:
        word, data = text.split(None, 1)
    except ValueError:
        event.notice_doc()
        return

    word = word.lower()
    try:
        old_data = factoid_cache[chan][word]
    except LookupError:
        old_data = None

    if data.startswith("+") and old_data:
        # remove + symbol
        new_data = data[1:]
        # append new_data to the old_data
        puncts = string.punctuation + " "
        if len(new_data) > 1 and new_data[1] in puncts:
            data = old_data + new_data
        else:
            data = old_data + " " + new_data
        notice("Appending \x02{}\x02 to \x02{}\x02".format(new_data, old_data))
    else:
        notice(
            "Remembering \x02{0}\x02 for \x02{1}\x02. Type {2}{1} to see it.".format(
                data, word, FACTOID_CHAR
            )
        )
        if old_data:
            notice("Previous data was \x02{}\x02".format(old_data))

    add_factoid(db, word, chan, data, nick)


def paste_facts(facts, raise_on_no_paste=False):
    headers = ("Command", "Output")
    data = [(FACTOID_CHAR + fact[0], fact[1]) for fact in sorted(facts.items())]
    tbl = gen_markdown_table(headers, data).encode("UTF-8")
    return web.paste(tbl, "md", "hastebin", raise_on_no_paste=raise_on_no_paste)


def remove_fact(chan, names, db, notice):
    found = {}
    missing = []
    for name in names:
        data = factoid_cache[chan].get(name.lower())
        if data:
            found[name] = data
        else:
            missing.append(name)

    if missing:
        notice(
            "Unknown factoids: {}".format(
                get_text_list([repr(s) for s in missing], "and")
            )
        )

    if found:
        try:
            notice("Removed Data: {}".format(paste_facts(found, True)))
        except NoPasteException:
            notice("Unable to paste removed data, not removing facts")
            return

        del_factoid(db, chan, list(found.keys()))


@hook.command("f", "forget", permissions=["op", "chanop"])
def forget(text, chan, db, notice):
    """<word>... - Remove factoids with the specified names"""
    remove_fact(chan, text.split(), db, notice)


@hook.command(
    "forgetall", "clearfacts", autohelp=False, permissions=["op", "chanop"]
)
def forget_all(chan, db):
    """- Remove all factoids in the current channel"""
    del_factoid(db, chan)
    return "Facts cleared."


@hook.command()
def info(text, chan, notice):
    """<factoid> - shows the source of a factoid"""

    text = text.strip().lower()

    if text in factoid_cache[chan]:
        notice(factoid_cache[chan][text])
    else:
        notice("Unknown Factoid.")


factoid_re = re.compile(r"^{} ?(.+)".format(re.escape(FACTOID_CHAR)), re.I)


@hook.regex(factoid_re)
def factoid(content, match, chan, message, action):
    """<word> - shows what data is associated with <word>"""
    arg1 = ""
    if len(content.split()) >= 2:
        arg1 = content.split()[1]
    # split up the input
    split = match.group(1).strip().split(" ")
    factoid_id = split[0].lower()

    if factoid_id in factoid_cache[chan]:
        data = factoid_cache[chan][factoid_id]
        result = data

        # factoid post-processors
        result = colors.parse(result)
        if arg1:
            result = result.replace("<user>", arg1)
        if result.startswith("<act>"):
            result = result[5:].strip()
            action(result)
        else:
            message(result)


@hook.command("listfacts", autohelp=False)
def listfactoids(notice, chan):
    """- lists all available factoids"""
    reply_text: List[str] = []
    reply_text_length = 0
    for word in sorted(factoid_cache[chan].keys()):
        text = FACTOID_CHAR + word
        added_length = len(text) + 2
        if reply_text_length + added_length > 400:
            notice(", ".join(reply_text))
            reply_text = []
            reply_text_length = 0

        reply_text.append(text)
        reply_text_length += added_length

    notice(", ".join(reply_text))


@hook.command("listdetailedfacts", autohelp=False)
def listdetailedfactoids(chan):
    """- lists all available factoids with their respective data"""
    return paste_facts(factoid_cache[chan])
