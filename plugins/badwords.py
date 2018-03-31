import re
from collections import defaultdict

from sqlalchemy import Table, Column, String, PrimaryKeyConstraint, select

from cloudbot import hook
from cloudbot.event import EventType
from cloudbot.util import database

table = Table(
    'badwords',
    database.metadata,
    Column('word', String),
    Column('nick', String),
    Column('chan', String),
    PrimaryKeyConstraint('word', 'chan')
)

badcache = defaultdict(list)


@hook.on_start()
@hook.command("loadbad", permissions=["badwords"], autohelp=False)
def load_bad(event):
    """- Should run on start of bot to load the existing words into the regex"""
    global badword_re
    badcache.clear()
    words = []

    with event.db_session() as db:
        for chan, word in db.execute(select([table.c.chan, table.c.word])):
            badcache[chan.casefold()].append(word)
            words.append(word)

    badword_re = re.compile(
        r'(\s|^|[^\w\s])({0})(\s|$|[^\w\s])'.format('|'.join(words)), re.IGNORECASE
    )


@hook.command("addbad", permissions=["badwords"])
def add_bad(text, nick, event):
    """<word> <channel> - adds a bad word to the auto kick list must specify a channel with each word"""
    splt = text.lower().split(None, 1)
    word, channel = splt
    if not event.is_channel(channel):
        return "Please specify a valid channel name after the bad word."

    word = re.escape(word)
    wordlist = list_bad(channel)
    if word in wordlist:
        return "{} is already added to the bad word list for {}".format(
            word, channel
        )

    if len(badcache[channel]) >= 10:
        return "There are too many words listed for channel {}. Please remove a word using .rmbad before adding anymore. For a list of bad words use .listbad".format(
            channel
        )

    with event.db_session() as db:
        db.execute(table.insert().values(word=word, nick=nick, chan=channel))
        db.commit()

    load_bad(event)
    wordlist = list_bad(channel)
    return "Current badwords: {}".format(wordlist)


@hook.command("rmbad", "delbad", permissions=["badwords"])
def del_bad(text, event):
    """<word> <channel> - removes the specified word from the specified channels bad word list"""
    splt = text.lower().split(None, 1)
    word, channel = splt
    if not event.is_channel(channel):
        return "Please specify a valid channel name after the bad word."

    with event.db_session() as db:
        db.execute(table.delete().where(table.c.word == word).where(table.c.chan == channel))
        db.commit()

    load_bad(event)
    newlist = list_bad(channel)
    return "Removing {} new bad word list for {} is: {}".format(
        word, channel, newlist
    )


@hook.command("listbad", permissions=["badwords"])
def list_bad(text, event):
    """<channel> - Returns a list of bad words specify a channel to see words for a particular channel"""
    text = text.split(' ')[0].lower()
    if not event.is_channel(text):
        return "Please specify a valid channel name"

    return '|'.join(badcache[text])


@hook.event([EventType.message, EventType.action], singlethread=True)
def test_badwords(conn, message, chan, content, nick):
    match = badword_re.match(content)
    if not match:
        return

    # Check to see if the match is for this channel
    word = match.group().lower().strip()
    if word in badcache[chan]:
        conn.cmd("KICK", chan, nick, "that fucking word is so damn offensive")
        message("{}, congratulations you've won!".format(nick))
